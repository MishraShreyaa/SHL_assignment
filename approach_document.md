# Approach Document

**Project:** SHL Assessment Recommendation Agent
**Author:** [Your Name]

## Architecture

The agent follows a standard retrieval-augmented generation (RAG)
pipeline, kept deliberately small:

1. **Guardrails** (`guardrails.py`) run first on every user message,
   using keyword matching to catch prompt injection, off-topic
   requests, and requests for non-SHL products. This is cheap, fast,
   and easy to reason about - no LLM call is wasted on messages we're
   going to refuse anyway.
2. **Retrieval** (`retriever.py`) embeds the SHL catalog once at
   startup with `sentence-transformers` (`all-MiniLM-L6-v2`, a small,
   fast model) and searches it with a FAISS flat index using cosine
   similarity. The query text is the full conversation so far, so
   context from earlier turns (e.g. "Java developer" mentioned two
   turns ago) still influences retrieval on later turns.
3. **Generation** (`chatbot.py`) sends the retrieved candidates plus
   the conversation history to Gemini 2.5 Flash, with a system prompt
   that forces it to (a) only recommend from the given candidates, (b)
   ask exactly one clarifying question if information is missing, and
   (c) always answer in one fixed JSON shape.
4. **Validation**: before the response leaves the server, every
   recommended item's name is checked against the real catalog
   (`_build_recommendations`). If Gemini ever hallucinates a name, it
   is silently dropped rather than shown to the user. This is the
   actual anti-hallucination guarantee - the prompt is the first line
   of defence, this check is the real one.

## Design Choices

**Why FastAPI.** The assignment requires two REST endpoints with a
strict JSON schema. FastAPI gives free request/response validation
via Pydantic models (`models.py`), auto-generated docs, and is simple
enough that the whole HTTP layer (`routes.py`, `main.py`) fits in
under 60 lines combined.

**Why Gemini 2.5 Flash.** It's fast and has a generous free tier,
which matters for an 8-turn, 30-second-per-call evaluator. I used the
raw `google-generativeai` SDK instead of LangChain: the only thing I
need from an LLM library here is "send a prompt, get text back", and
LangChain's abstractions (chains, output parsers) would add a layer of
indirection without saving meaningful code, given the assignment's
explicit push toward simplicity.

**Why FAISS.** It's the simplest widely-used vector search library
that doesn't need a separate running service (unlike, say, a hosted
vector DB) - just a Python object built once at startup. For a catalog
of a few hundred items, an exact `IndexFlatIP` (cosine similarity via
normalized inner product) is fast enough that approximate indexes
would be premature optimisation.

**Why JSON for storage instead of a database.** The catalog is
read-only at runtime and small enough to fit in memory. Adding
Postgres/Mongo would mean provisioning and connecting to another
service on Render for no real benefit at this scale - directly against
the "no unnecessary complexity" guidance.

## Prompt Design

The system prompt (`prompts.py`) does three jobs: (1) states the hard
rule that only candidates in the given list may be recommended, (2)
enforces "ask exactly one question" as an explicit rule rather than
hoping the model infers it, and (3) locks the output to one JSON
shape, including the rule that `recommendations` must be empty while
clarifying/refusing and 1-10 items when recommending. Putting the
schema directly in the prompt (rather than a separate "classify intent
then generate" call) keeps the pipeline to a single LLM call per
turn, which matters under the 30-second timeout.

## Retrieval Strategy

Each catalog item is embedded as `"{name}. {description} Skills:
{skills}. Category: {category}."` - combining these fields means a
query like "Java developer" matches on skills/description even when
the exact word doesn't appear in the assessment's name. The query
embedded at search time is the whole conversation transcript, not just
the latest message, so a shortlist naturally reflects everything the
user has said so far (important for the "refine" behaviour - "also
add personality tests" only makes sense combined with earlier turns).

## Evaluation Strategy

Given the sandboxed dev environment had no internet access, formal
evaluation against the public conversation traces and a live Gemini
key wasn't possible here. What I did instead:

- Unit tests (`tests/test_guardrails.py`, `tests/test_utils.py`) cover
  the two riskiest, LLM-independent pieces: does the keyword filter
  correctly catch injection/off-topic messages without false-positiving
  on legitimate SHL questions, and does the JSON extractor correctly
  handle Gemini's common output quirks (markdown fences, stray text).
- `tests/sample_conversations.md` documents expected behaviour for
  each of the seven required conversation patterns (normal, vague,
  refinement, comparison, injection, off-topic, missing info), written
  against the actual code paths so a reviewer (or the real evaluator)
  can check outputs by hand.
- **What I'd add with internet access**: a script that replays the 10
  provided public traces against a running `/chat` endpoint and
  computes Recall@10 automatically, per the assignment's own formula.

## Limitations

- `data/shl_catalog.json` ships as a **hand-curated sample** (32
  Individual Test Solutions covering cognitive, personality,
  technical-skill, and situational-judgement categories), not a live
  scrape, because this project was built without internet access.
  `scripts/scrape_catalog.py` is written and ready to run against the
  real SHL catalog - running it will replace the sample file with live
  data. Anyone grading this should run the scraper before treating the
  catalog as authoritative.
- Guardrails are keyword-based, so a cleverly-worded off-topic request
  could slip past the first layer - the system prompt is a second
  layer, but a model-based classifier would be more robust long term.
- The retriever treats every catalog item independently; it doesn't
  yet model relationships like "a battery" of tests bundled together.
