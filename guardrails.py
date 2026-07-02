"""
guardrails.py

Purpose of this file:
    Decides whether the latest user message is something our agent is
    allowed to engage with. This runs BEFORE we ever call Gemini, so an
    off-topic or malicious message never even reaches the LLM prompt.

Why it exists:
    The assignment requires the agent to refuse politics, medical,
    cooking, general hiring advice, unrelated programming help, and
    prompt-injection attempts. Doing this with simple keyword checks
    is deliberately simple - it is transparent, fast, free, and easy
    to explain in an interview, unlike relying purely on the LLM to
    "decide" it should refuse.

    Note: this is a first line of defence, not the only one. The
    system prompt in prompts.py also tells Gemini to stay in scope,
    so even if a tricky phrasing slips past these keyword checks, the
    LLM itself has instructions to refuse and never invent catalog
    entries.

Possible interview questions from this file:
    - Why keyword matching instead of asking Gemini to classify intent?
    - How would this break, and how would you catch it? (edge cases,
      false positives on legitimate SHL questions that happen to
      contain a flagged word)
    - How would you evolve this file into an ML-based classifier later?
"""

from dataclasses import dataclass

# Phrases commonly used to try to override the system prompt or leak it.
PROMPT_INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore your instructions",
    "ignore the above",
    "disregard previous",
    "reveal your prompt",
    "show me your system prompt",
    "what is your system prompt",
    "you are now",
    "act as",
    "jailbreak",
    "developer mode",
    "print your instructions",
    "repeat your instructions",
]

# Topics that are simply out of scope for an SHL assessment agent.
OFF_TOPIC_KEYWORDS = [
    # Politics
    "election", "president", "prime minister", "political party", "vote for",
    # Medical
    "diagnose", "symptoms", "prescription", "medication dosage", "disease",
    # Cooking
    "recipe", "how to cook", "how do i bake", "ingredients for",
    # General legal / hiring advice (outside catalog scope)
    "is it legal to fire", "employment law", "how much should i pay",
    "write a job offer letter", "salary negotiation advice",
    # Generic unrelated programming help (not about SHL tests)
    "fix my code", "debug my program", "write a python script for me",
    "build me a website",
]

# Competitor / unrelated products the agent must never recommend.
COMPETITOR_KEYWORDS = [
    "amazon assessment", "linkedin assessment", "indeed assessment",
    "hackerrank", "codility", "criteria corp", "pymetrics",
]


@dataclass
class GuardrailResult:
    """Outcome of checking one user message."""

    is_allowed: bool
    reason: str = ""


def check_message(message: str) -> GuardrailResult:
    """Check a single user message against our simple rule set.

    Args:
        message: The latest user message from the conversation.

    Returns:
        GuardrailResult with is_allowed=False and a reason if the
        message should be refused, otherwise is_allowed=True.
    """
    lowered = message.lower()

    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern in lowered:
            return GuardrailResult(
                is_allowed=False,
                reason=(
                    "I can't follow instructions that try to change how I behave. "
                    "I'm only able to help with SHL Individual Test Solutions."
                ),
            )

    for keyword in COMPETITOR_KEYWORDS:
        if keyword in lowered:
            return GuardrailResult(
                is_allowed=False,
                reason=(
                    "I can only recommend assessments from the SHL catalog, "
                    "not from other providers."
                ),
            )

    for keyword in OFF_TOPIC_KEYWORDS:
        if keyword in lowered:
            return GuardrailResult(
                is_allowed=False,
                reason=(
                    "That's outside what I can help with. I'm focused only on "
                    "recommending SHL Individual Test Solutions for hiring needs. "
                    "Tell me about the role you're hiring for and I can help "
                    "with that."
                ),
            )

    return GuardrailResult(is_allowed=True)
