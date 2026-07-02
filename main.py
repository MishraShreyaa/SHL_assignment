"""
main.py

Purpose of this file:
    Creates the FastAPI app, wires in the /health and /chat routes,
    and loads the catalog + builds the FAISS index once at startup.

Why it exists:
    This is the single entry point uvicorn runs
    ("uvicorn app.main:app"). Building the retriever here (instead of
    inside routes.py) means embeddings are computed exactly once per
    process start, not once per request.

Possible interview questions from this file:
    - Why use FastAPI's startup event instead of building the
      retriever at import time?
    - What would happen on Render's free tier if we rebuilt embeddings
      on every request instead of once at startup?
"""

from fastapi import FastAPI

from app.catalog_loader import load_catalog
from app.retriever import CatalogRetriever
from app.routes import router

app = FastAPI(
    title="SHL Assessment Recommendation Agent",
    description="A conversational agent that recommends SHL Individual Test Solutions.",
    version="1.0.0",
)

app.include_router(router)


@app.on_event("startup")
def startup_event() -> None:
    """Load the catalog and build the FAISS index once, then stash the
    retriever on app.state so route handlers can reuse it."""
    catalog = load_catalog()
    app.state.retriever = CatalogRetriever(catalog)
