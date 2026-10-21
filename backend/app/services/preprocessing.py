"""
Preprocessing service.

Two responsibilities, both built on app.utils.text.normalize_text so
every text source is treated identically (Section 12):

1. preprocess_query() — normalize a raw user question before it's
   TF-IDF-transformed and compared against the corpus (Phase 4).
2. build_retrieval_text() — build the per-record corpus string that the
   TF-IDF vectorizer is fit against, combining canonical_question +
   alternative_user_questions + keywords (Section 13). The answer text
   is deliberately excluded from this corpus — we're matching the
   user's *intent* against the FAQ's *question*, not against its answer.
"""

from app.models.schemas import FAQRecord
from app.utils.text import normalize_text


def preprocess_query(user_query: str) -> str:
    """Normalize a raw user query for retrieval matching."""
    return normalize_text(user_query)


def build_retrieval_text(record: FAQRecord) -> str:
    """
    Build the normalized retrieval text for one FAQ record.

    Combines canonical_question, all alternative_user_questions, and all
    keywords into one string, each piece normalized individually before
    joining (so punctuation at a join boundary can't accidentally fuse
    two words together).

    Duplicate normalized parts are collapsed to a single occurrence
    (order-preserving). This matters in practice: several records in the
    real knowledge base repeat the canonical question verbatim inside
    alternative_user_questions (e.g. FAQ-037's canonical "What is the
    SAT?" appears a second time, word-for-word, as an "alternative").
    Without deduplication, that record's retrieval text contains "what
    is the sat" four times over, which inflates the TF-IDF weight of the
    generic words "what"/"is"/"the" for that one record and made it
    falsely match unrelated "What is the X?" queries (observed during
    Phase 6 threshold testing: "What is the capital of France?" scored
    0.36 against FAQ-037 — above the 0.30 fallback threshold — purely
    because of this repetition, not real topical overlap). Deduplicating
    here fixes the corpus itself without touching the source JSON.
    """
    parts: list[str] = [record.canonical_question]
    parts.extend(record.alternative_user_questions)
    parts.extend(record.keywords)

    normalized_parts = [normalize_text(p) for p in parts if p]
    normalized_parts = [p for p in normalized_parts if p]

    deduped_parts: list[str] = []
    seen: set[str] = set()
    for part in normalized_parts:
        if part not in seen:
            deduped_parts.append(part)
            seen.add(part)

    return " ".join(deduped_parts)


def build_corpus(records: list[FAQRecord]) -> list[str]:
    """
    Build the full retrieval corpus: one retrieval-text string per
    record, in the same order as `records`, so index i of the corpus
    always corresponds to records[i]. The TF-IDF vectorizer (Phase 4)
    is fit against this list.
    """
    return [build_retrieval_text(record) for record in records]
