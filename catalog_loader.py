"""
catalog_loader.py

Purpose of this file:
    Loads data/shl_catalog.json from disk into a list of AssessmentItem
    objects that the rest of the app can use.

Why it exists:
    Keeping "read the JSON file" separate from "search the catalog"
    (retriever.py) makes both pieces easier to test on their own. If
    we ever swap JSON for a real database, only this file changes.

Possible interview questions from this file:
    - Why cache the catalog instead of reading the file on every request?
    - What happens if the JSON file is malformed?
    - How would you extend this to load from a database instead of a file?
"""

import json
from pathlib import Path
from typing import List

from app.config import CATALOG_PATH
from app.models import AssessmentItem

# Simple in-memory cache so we only read/parse the file once per process,
# not on every single API call.
_catalog_cache: List[AssessmentItem] = []


def load_catalog(path: str = CATALOG_PATH) -> List[AssessmentItem]:
    """Read the SHL catalog JSON file and return a list of AssessmentItem.

    Args:
        path: Path to the catalog JSON file. Defaults to the value in
            config.py so tests can point to a smaller fixture file.

    Returns:
        A list of validated AssessmentItem objects.

    Raises:
        FileNotFoundError: if the catalog file does not exist.
        ValueError: if the file is not valid JSON or fails validation.
    """
    global _catalog_cache

    catalog_path = Path(path)
    if not catalog_path.exists():
        raise FileNotFoundError(f"Catalog file not found at: {catalog_path}")

    with open(catalog_path, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    items: List[AssessmentItem] = [AssessmentItem(**item) for item in raw_items]
    _catalog_cache = items
    return items


def get_cached_catalog() -> List[AssessmentItem]:
    """Return the already-loaded catalog, loading it first if needed.

    This is the function most other modules should call - it avoids
    re-reading the file from disk every time.
    """
    if not _catalog_cache:
        return load_catalog()
    return _catalog_cache
