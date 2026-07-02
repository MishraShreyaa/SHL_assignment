"""
chatbot.py

Purpose of this file:
    The brain of the agent. Given the full conversation history, this
    file decides what to do next: refuse, ask a clarifying question,
    or retrieve + recommend assessments. This is where guardrails,
    retrieval and the Gemini call all come together.

Why it exists:
    Splitting this out from routes.py keeps the FastAPI layer "thin" -
    routes.py only knows about HTTP, chatbot.py only knows about
    conversation logic. That separation makes both pieces easier to
    test and reason about.

Possible interview questions from this file:
    - Walk me through what happens for a single POST /chat call.
    - Why run guardrails before retrieval instead of after?
    - What happens if Gemini returns something that isn't valid JSON?
    - How do you stop Gemini from recommending something not in the
      retrieved candidate list?
"""

import json
from typing import List

import google.generativeai as genai

from app.config import GEMINI_API_KEY, GEMINI_MODEL_NAME, TOP_K
from app.guardrails import check_message
from app.models import AssessmentItem, ChatResponse, Message, Recommendation
from app.prompts import (
    NORMAL_STAGE_HINT,
    REFUSAL_STAGE_HINT,
    SYSTEM_INSTRUCTIONS,
    USER_PROMPT_TEMPLATE,
)
from app.retriever import CatalogRetriever
from app.utils import build_conversation_text, extract_json_from_text

# Configure the Gemini SDK once when this module is imported.
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

_gemini_model = None


def _get_gemini_model():
    """Lazily create the Gemini model client so importing this module
    never fails just because an API key is missing (useful for tests)."""
    global _gemini_model
    if _gemini_model is None:
        _gemini_model = genai.GenerativeModel(
            model_name=GEMINI_MODEL_NAME,
            system_instruction=SYSTEM_INSTRUCTIONS,
        )
    return _gemini_model


def _format_candidates(items: List[AssessmentItem]) -> str:
    """Turn retrieved catalog items into a compact JSON block Gemini
    can read. We only include fields the model actually needs, to
    keep the prompt small and avoid distracting it with duration etc."""
    compact = [
        {
            "name": item.name,
            "description": item.description,
            "skills": item.skills,
            "test_type": item.test_type,
            "url": item.url,
        }
        for item in items
    ]
    return json.dumps(compact, indent=2)


def _fallback_response(reply_text: str) -> ChatResponse:
    """A safe response used whenever something goes wrong (guardrail
    refusal, unparsable LLM output, etc). Always schema-valid."""
    return ChatResponse(reply=reply_text, recommendations=[], end_of_conversation=False)


def _build_recommendations(
    raw_items: List[dict], catalog_lookup: dict
) -> List[Recommendation]:
    """Validate Gemini's recommended items against the real catalog.

    Even though our prompt tells Gemini to only use the given
    candidates, we double check here so a hallucinated name can never
    reach the user - this is the actual guarantee, the prompt is just
    the first layer.
    """
    safe_recommendations: List[Recommendation] = []
    for raw in raw_items:
        name = raw.get("name", "")
        # Only accept items whose name matches something in our catalog.
        matched_item = catalog_lookup.get(name)
        if matched_item is None:
            continue
        safe_recommendations.append(
            Recommendation(
                name=matched_item.name,
                url=matched_item.url,
                test_type=matched_item.test_type,
            )
        )
    return safe_recommendations[:10]


def generate_reply(
    messages: List[Message], retriever: CatalogRetriever
) -> ChatResponse:
    """Main entry point: given the conversation so far, return the
    agent's next reply.

    Args:
        messages: Full conversation history sent by the client.
        retriever: A ready-to-use CatalogRetriever built at app startup.

    Returns:
        A schema-valid ChatResponse.
    """
    if not messages:
        return _fallback_response(
            "Hi! Tell me about the role you're hiring for and I can "
            "recommend SHL assessments for it."
        )

    latest_user_message = messages[-1].content

    # Step 1: guardrails run before we spend any tokens on the LLM.
    guardrail_result = check_message(latest_user_message)

    history_text = build_conversation_text(messages)

    if not guardrail_result.is_allowed:
        candidates_text = "[]"
        stage_hint = REFUSAL_STAGE_HINT
    else:
        # Step 2: retrieve grounding candidates from FAISS using the
        # whole conversation so far (captures context from earlier turns).
        retrieved_items = retriever.search(history_text, top_k=TOP_K)
        candidates_text = _format_candidates(retrieved_items)
        stage_hint = NORMAL_STAGE_HINT

    prompt = USER_PROMPT_TEMPLATE.format(
        history=history_text,
        candidates=candidates_text,
        stage_hint=stage_hint,
    )

    try:
        model = _get_gemini_model()
        result = model.generate_content(prompt)
        response_text = result.text
    except Exception:
        # Network hiccup, quota issue, etc - fail safely instead of 500ing.
        return _fallback_response(
            "I'm having trouble reaching the assessment engine right now. "
            "Please try again in a moment."
        )

    parsed = extract_json_from_text(response_text)
    if parsed is None:
        return _fallback_response(
            "Sorry, I had trouble putting that together. Could you rephrase "
            "what you're hiring for?"
        )

    catalog_lookup = {item.name: item for item in retriever.catalog}
    recommendations = _build_recommendations(
        parsed.get("recommendations", []), catalog_lookup
    )

    return ChatResponse(
        reply=parsed.get("reply", ""),
        recommendations=recommendations,
        end_of_conversation=bool(parsed.get("end_of_conversation", False)),
    )
