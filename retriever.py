"""
retriever.py

Purpose of this file:
    Turns the SHL catalog into sentence embeddings, builds a FAISS
    index over them, and exposes a simple search(query, top_k) function
    that returns the most relevant catalog items for a piece of text.

Why it exists:
    Gemini should never be left to "remember" the SHL catalog from its
    own training data - that is how you get hallucinated test names and
    made-up URLs. Instead we do old-fashioned semantic search first and
    only ever show Gemini the items we actually found. This is the
    "retrieval" half of RAG (Retrieval-Augmented Generation).

Possible interview questions from this file:
    - Why FAISS instead of a plain cosine-similarity loop?
    - Why normalize embeddings before adding them to the index?
    - What would you change to make this scale to 100,000 catalog items?
    - Why build the index once at startup instead of per-request?
"""

from typing import List

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import EMBEDDING_MODEL_NAME, TOP_K
from app.models import AssessmentItem


class CatalogRetriever:
    """Wraps a FAISS index + the sentence-transformers model used to
    build it, so callers only ever deal with plain text in and
    AssessmentItem objects out."""

    def __init__(self, catalog: List[AssessmentItem]) -> None:
        self.catalog = catalog
        self.model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        self.index = self._build_index(catalog)

    def _catalog_item_to_text(self, item: AssessmentItem) -> str:
        """Combine the fields that matter for search into one string.

        We include the name, description and skills because a query
        like "Java developer" should match on skills/description even
        if the word "Java" is not in the assessment name.
        """
        skills_text = ", ".join(item.skills)
        return f"{item.name}. {item.description} Skills: {skills_text}. Category: {item.category}."

    def _build_index(self, catalog: List[AssessmentItem]) -> faiss.IndexFlatIP:
        """Embed every catalog item once and load the vectors into a
        FAISS index that supports cosine-similarity search."""
        texts = [self._catalog_item_to_text(item) for item in catalog]
        embeddings = self.model.encode(texts, convert_to_numpy=True)

        # Normalizing vectors + using inner product (IP) is a standard
        # trick to get cosine similarity search out of FAISS.
        faiss.normalize_L2(embeddings)

        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)
        index.add(embeddings)
        return index

    def search(self, query: str, top_k: int = TOP_K) -> List[AssessmentItem]:
        """Return the top_k catalog items most similar to the query text.

        Args:
            query: Free text describing what the hiring manager needs,
                usually built from the conversation so far.
            top_k: How many results to return.

        Returns:
            A list of AssessmentItem, best match first.
        """
        if not query.strip():
            return []

        query_vector = self.model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_vector)

        top_k = min(top_k, len(self.catalog))
        _distances, indices = self.index.search(query_vector, top_k)

        # indices is a 2D array (1 row per query); we only sent one query.
        return [self.catalog[i] for i in indices[0] if i != -1]
