"""
config.py

Purpose of this file:
    Central place to read all environment variables and project-wide
    constants. Every other file imports settings from here instead of
    calling os.getenv() everywhere, so if a setting name ever changes
    we only have to change it in one place.

Why it exists:
    Hardcoding API keys / model names inside chatbot logic makes the
    code hard to test and hard to deploy on different environments
    (local vs Render). Keeping it in one small file fixes that.

Possible interview questions from this file:
    - Why use python-dotenv instead of just os.environ?
    - What happens if GEMINI_API_KEY is missing?
    - Why is TOP_K a constant instead of hardcoded inside retriever.py?
"""

import os
from dotenv import load_dotenv

# Load variables from a local .env file (if it exists) into the
# process environment. On Render, real environment variables are set
# in the dashboard, so load_dotenv() simply does nothing there.
load_dotenv()

# ---- Gemini settings -------------------------------------------------
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL_NAME: str = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")

# ---- Embedding / retrieval settings -----------------------------------
# Small and fast model, good enough for a catalog of a few hundred items.
EMBEDDING_MODEL_NAME: str = os.getenv(
    "EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2"
)
# How many catalog items we hand to Gemini as grounding context.
TOP_K: int = int(os.getenv("TOP_K", "10"))

# ---- Data settings -----------------------------------------------------
CATALOG_PATH: str = os.getenv("CATALOG_PATH", "data/shl_catalog.json")

# ---- Conversation limits (must match the SHL assignment spec) ----------
MAX_TURNS: int = int(os.getenv("MAX_TURNS", "8"))
MIN_RECOMMENDATIONS: int = 1
MAX_RECOMMENDATIONS: int = 10
