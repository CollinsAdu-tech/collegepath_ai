"""
Tests for the preprocessing layer (Section 38 — Preprocessing tests).

Covers:
- lowercase conversion
- whitespace normalization
- punctuation handling
- empty input
- meaningful-word preservation (Section 12's explicit example)
- retrieval-text construction from a real FAQRecord
"""

import pytest

from app.core.config import settings
from app.models.schemas import FAQRecord
from app.services.knowledge_base import KnowledgeBaseService
from app.services.preprocessing import (
    build_corpus,
    build_retrieval_text,
    preprocess_query,
)
from app.utils.text import normalize_text


# --- normalize_text / preprocess_query ---

def test_lowercase_conversion():
    assert normalize_text("What Is EARLY ACTION?") == "what is early action"


def test_whitespace_normalization_collapses_and_strips():
    assert normalize_text("  What   is\t\tEarly\nAction?  ") == "what is early action"


def test_punctuation_is_stripped_but_words_survive():
    result = normalize_text("Can I apply to college after a gap year?!")
    assert result == "can i apply to college after a gap year"


def test_apostrophes_dont_glue_words_together():
    # "don't" should not become "dont" merged into a neighboring word,
    # and should not disappear entirely — it becomes "don t", which
    # still tokenizes to two separate, meaningful stems for TF-IDF.
    result = normalize_text("What if I don't have a passport?")
    assert "don" in result.split()
    assert "t" in result.split()


def test_empty_input_returns_empty_string():
    assert normalize_text("") == ""
    assert normalize_text("   ") == ""


def test_non_string_input_raises_type_error():
    with pytest.raises(TypeError):
        normalize_text(None)  # type: ignore[arg-type]


def test_preserves_meaningful_admissions_terms():
    # Section 12's explicit example: these words must all survive intact.
    result = preprocess_query("Can international students receive financial aid?")
    for term in ["international", "students", "financial", "aid"]:
        assert term in result.split()


def test_numbers_are_preserved():
    result = normalize_text("What is the deadline for Fall 2027 admission?")
    assert "2027" in result.split()


def test_preprocess_query_is_just_normalize_text():
    query = "What is Early Action??"
    assert preprocess_query(query) == normalize_text(query)


# --- build_retrieval_text / build_corpus ---

def make_record(**overrides) -> FAQRecord:
    base = dict(
        id="TEST-001",
        category="Testing",
        canonical_question="What is the SAT?",
        alternative_user_questions=["Can you explain the SAT?", "What's the SAT test?"],
        answer="The SAT is a standardized test.",
        source_hierarchy=[],
        source_urls=[],
        information_type="policy_dependent",
        verification_date="2026-09-20",
        keywords=["sat", "testing", "standardized-test"],
        confidence=0.95,
        update_rule="Verify each admission cycle.",
        dynamic=True,
        requires_current_verification=True,
        follow_up_questions=[],
    )
    base.update(overrides)
    return FAQRecord(**base)


def test_build_retrieval_text_combines_all_three_fields():
    record = make_record()
    text = build_retrieval_text(record)
    # canonical question terms
    assert "sat" in text
    # alternative question terms
    assert "explain" in text
    # keyword terms (hyphen becomes a space, so "standardized" and "test"
    # survive as separate tokens)
    assert "standardized" in text
    assert "testing" in text


def test_build_retrieval_text_excludes_answer_text():
    record = make_record(answer="This sentence contains a unique term xylophone123.")
    text = build_retrieval_text(record)
    assert "xylophone123" not in text


def test_build_retrieval_text_is_fully_normalized():
    record = make_record(canonical_question="What Is THE SAT???")
    text = build_retrieval_text(record)
    assert text == text.lower()
    assert "?" not in text


def test_build_retrieval_text_handles_empty_keywords_and_alternatives():
    record = make_record(alternative_user_questions=[], keywords=[])
    text = build_retrieval_text(record)
    assert text == normalize_text(record.canonical_question)


def test_build_corpus_preserves_record_order():
    records = [
        make_record(id="A", canonical_question="What is Early Action?"),
        make_record(id="B", canonical_question="What is a gap year?"),
    ]
    corpus = build_corpus(records)
    assert len(corpus) == 2
    assert "action" in corpus[0]
    assert "gap" in corpus[1]


# --- Integration with the real knowledge base ---

@pytest.fixture
def loaded_kb() -> KnowledgeBaseService:
    kb = KnowledgeBaseService(settings.KNOWLEDGE_BASE_PATH)
    kb.load()
    return kb


def test_corpus_builds_for_entire_real_knowledge_base(loaded_kb: KnowledgeBaseService):
    corpus = build_corpus(loaded_kb.records)
    assert len(corpus) == len(loaded_kb.records) == 147
    # No entry should be empty — every record has at least a canonical question.
    assert all(entry.strip() != "" for entry in corpus)


def test_real_gap_year_record_retrieval_text_contains_expected_terms(
    loaded_kb: KnowledgeBaseService,
):
    gap_year_records = loaded_kb.get_by_category("Gap Years")
    combined = " ".join(build_retrieval_text(r) for r in gap_year_records)
    assert "gap" in combined
    assert "year" in combined
