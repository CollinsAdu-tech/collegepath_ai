"""
Centralized configuration for CollegePath AI.

Every tunable value referenced elsewhere in the app (retrieval threshold,
top-k, query length limits, CORS origins, the knowledge base path) is
defined here and read from environment variables where relevant. This
keeps "magic numbers" out of the business logic and makes threshold
tuning (Phase 6 / Section 40) a config change, not a code change.
"""

import os
from pathlib import Path

# Resolve paths relative to this file so the app works regardless of
# the working directory it's launched from.
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
DATA_DIR = BASE_DIR / "data"
KNOWLEDGE_BASE_PATH = DATA_DIR / "CollegePath_AI_Master_Knowledge_Base_v1.json"


class Settings:
    """Application settings, overridable via environment variables."""

    # --- App metadata ---
    APP_NAME: str = "CollegePath AI"
    APP_VERSION: str = "0.1.0"

    # --- Retrieval configuration (Section 17 / 50) ---
    # Section 17 suggests 0.30 as a starting point. Phase 6 testing found
    # that value too permissive for this corpus: an informal 18-query
    # evaluation (10 on-domain, 8 clearly off-domain) showed on-domain and
    # off-domain top-1 similarity scores overlapping in the 0.27-0.39
    # range. At 0.30, three off-domain queries ("What is the capital of
    # France?", "Write me a Python game.", "What is the weather today?")
    # scored high enough to be confidently (and wrongly) answered. Raising
    # the threshold to 0.40 was the first value that eliminated all
    # observed off-domain false positives, at the cost of one additional
    # on-domain false negative (a legitimate but sparsely-worded query
    # falls back instead of answering — recoverable by rephrasing, and a
    # safer failure mode than a confidently wrong answer per Section 18).
    # This is still a starting point, not a final answer — Section 39's
    # full 30-50 query evaluation (Phase 11) should confirm or refine it.
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.40"))
    TOP_K: int = int(os.getenv("TOP_K", "3"))

    # --- API input validation (Section 26 / 37) ---
    MAX_QUERY_LENGTH: int = int(os.getenv("MAX_QUERY_LENGTH", "500"))

    # --- CORS (Section 37) ---
    # Deliberately explicit rather than "*". Both localhost and 127.0.0.1
    # are listed for the Vite dev server: browsers treat these as two
    # DIFFERENT origins even though they reach the same machine, so a
    # developer opening the frontend via one while the other is the only
    # one allow-listed hits a silent CORS failure (confirmed during Phase
    # 10 integration testing — a GET /health request with
    # Origin: http://127.0.0.1:5173 came back with no
    # Access-Control-Allow-Origin header at all when only
    # http://localhost:5173 was allow-listed, which a real browser would
    # treat as a blocked cross-origin request even though the response
    # body itself was fine).
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")

    # --- Data source ---
    KNOWLEDGE_BASE_PATH: Path = Path(
        os.getenv("KNOWLEDGE_BASE_PATH", str(KNOWLEDGE_BASE_PATH))
    )


settings = Settings()
