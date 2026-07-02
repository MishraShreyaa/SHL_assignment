"""
test_utils.py

Purpose of this file:
    Unit tests for the JSON-extraction helper in app/utils.py, since
    Gemini's raw text output is the messiest part of the pipeline to
    parse reliably.
"""

from app.utils import extract_json_from_text


def test_parses_plain_json():
    text = '{"reply": "hello", "recommendations": [], "end_of_conversation": false}'
    result = extract_json_from_text(text)
    assert result["reply"] == "hello"


def test_parses_json_inside_markdown_fence():
    text = '```json\n{"reply": "hi there", "recommendations": []}\n```'
    result = extract_json_from_text(text)
    assert result["reply"] == "hi there"


def test_returns_none_for_garbage_text():
    text = "Sorry, I can't help with that."
    result = extract_json_from_text(text)
    assert result is None


def test_extracts_json_with_surrounding_text():
    text = 'Here is my answer:\n{"reply": "ok", "recommendations": []}\nHope that helps!'
    result = extract_json_from_text(text)
    assert result["reply"] == "ok"
