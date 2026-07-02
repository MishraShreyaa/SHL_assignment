"""
utils.py

Purpose of this file:
    Small, reusable helper functions that don't belong to any single
    module - mostly around parsing Gemini's raw text output into JSON.

Why it exists:
    LLMs often wrap JSON output in markdown code fences (```json ... ```)
    or add stray text before/after. Rather than repeating this cleanup
    logic in chatbot.py, it lives here once.

Possible interview questions from this file:
    - Why not use Gemini's built-in "JSON mode" / response_schema feature?
      (We do use it as the primary path - see chatbot.py - this function
      is the safety net for when that still returns messy text.)
    - What happens if Gemini's output truly cannot be parsed as JSON?
"""

import json
import re
from typing import Any, Optional


def extract_json_from_text(text: str) -> Optional[dict[str, Any]]:
    """Try to pull a JSON object out of a raw LLM response string.

    Handles the common case where the model wraps JSON in a markdown
    code fence, e.g.:

        ```json
        {"reply": "..."}
        ```

    Args:
        text: Raw text returned by the LLM.

    Returns:
        A parsed dict if JSON was found and valid, otherwise None.
    """
    if not text:
        return None

    # Strip ```json ... ``` or ``` ... ``` fences if present.
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    candidate = fence_match.group(1) if fence_match else text.strip()

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # Last resort: grab the first {...} block in the text.
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            return None

    return None


def build_conversation_text(messages: list) -> str:
    """Flatten a list of Message objects into one plain-text block,
    used both for building the retrieval query and for logging/debug.

    Args:
        messages: List of app.models.Message objects.

    Returns:
        A single string like "user: ...\\nassistant: ...\\n..."
    """
    lines = [f"{m.role}: {m.content}" for m in messages]
    return "\n".join(lines)


def count_conversation_turns(messages: list) -> int:
    """Count total turns (user + assistant messages) in the history.

    Used to enforce the 8-turn cap from the assignment.
    """
    return len(messages)
