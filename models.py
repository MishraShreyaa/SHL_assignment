"""
models.py

Purpose of this file:
    Defines every Pydantic model used by the API. This is the single
    source of truth for the request/response JSON shape that the SHL
    evaluator expects.

Why it exists:
    The assignment says the schema is "non-negotiable" - if we deviate,
    the automated evaluator fails us. Keeping all models in one file
    makes it easy to double-check we match the spec exactly.

Possible interview questions from this file:
    - Why use Pydantic instead of plain dicts?
    - How does FastAPI use these models to auto-generate docs/validation?
    - Why does Recommendation not include "description" even though the
      catalog has one? (Answer: the response schema in the assignment
      only asks for name, url, test_type - keeping the response small.)
"""

from typing import List, Literal
from pydantic import BaseModel, Field


class Message(BaseModel):
    """A single turn in the conversation history."""

    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """Body of POST /chat. The API is stateless, so the client must
    send the full conversation history on every call."""

    messages: List[Message]


class Recommendation(BaseModel):
    """One assessment suggested to the user."""

    name: str
    url: str
    test_type: str


class ChatResponse(BaseModel):
    """Body returned by POST /chat."""

    reply: str
    recommendations: List[Recommendation] = Field(default_factory=list)
    end_of_conversation: bool = False


class HealthResponse(BaseModel):
    """Body returned by GET /health."""

    status: str = "ok"


class AssessmentItem(BaseModel):
    """One row from data/shl_catalog.json. This is our internal
    representation, not the API response - the fields here are richer
    (description, skills, duration) than what we expose to the user."""

    name: str
    description: str
    skills: List[str]
    duration: int  # minutes
    category: str
    test_type: str
    url: str
