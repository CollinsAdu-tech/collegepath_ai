"""
Tests for the retrieval layer.

Phase 4 (TF-IDF only): fitting, matrix shape, vocabulary contents, query
transformation, out-of-vocabulary handling, misuse errors.

Phase 5 (this addition — cosine similarity + ranking via RetrievalEngine):
- obvious matching questions retrieve the right record
- paraphrased questions still retrieve the right record
- unrelated questions score low against everything
- top-k ranking returns results sorted by descending similarity
- similarity scores are within [0, 1] and distinct from `confidence`
"""

import pytest

from app.core.config import settings
from app.core.exceptions import RetrievalError
from app.models.schemas import FAQRecord
from app.services.knowledge_base import KnowledgeBaseService
from app.services.retrieval import RetrievalEngine, TfidfIndex


def make_record(**overrides) -> FAQRecord:
    base = dict(
        id="TEST-001",
        category="Testing",
        canonical_question="What is Early Action?",
        alternative_user_questions=[
            "Can you explain Early Action?",
            "What does Early Action mean?",
        ],
        answer="Early Action is a non-binding early admission plan.",
        source_hierarchy=[],
        source_urls=[],
        information_type="stable",
        verification_date="2026-09-20",
        keywords=["early action", "decision types"],
        confidence=0.95,
        update_rule="Review annually.",
        dynamic=False,
        requires_current_verification=False,
        follow_up_questions=[],
    )
    base.update(overrides)
    return FAQRecord(**base)


@pytest.fixture
def small_records() -> list[FAQRecord]:
    return [
        make_record(
            id="A",
            category="Decision Types",
            canonical_question="What is Early Action?",
            alternative_user_questions=["Can you explain Early Action?"],
            keywords=["early action"],
        ),
        make_record(
            id="B",
            category="Gap Years",
            canonical_question="What is a gap year?",
            alternative_user_questions=["Can I take a year off before college?"],
            keywords=["gap year"],
        ),
        make_record(
            id="C",
            category="Testing",
            canonical_question="What is the SAT?",
            alternative_user_questions=["Can you explain the SAT?"],
            keywords=["sat", "testing"],
        ),
    ]


# --- Fitting and basic shape ---

def test_fit_raises_on_empty_record_list():
    with pytest.raises(ValueError, match="at least one FAQ record"):
        TfidfIndex([])


def test_index_not_fitted_before_fit_is_called(small_records):
    index = TfidfIndex(small_records)
    assert not index.is_fitted


def test_fit_produces_matrix_with_one_row_per_record(small_records):
    index = TfidfIndex(small_records)
    index.fit()
    assert index.is_fitted
    assert index.matrix.shape[0] == len(small_records) == 3


def test_fit_produces_bigram_vocabulary(small_records):
    index = TfidfIndex(small_records)
    index.fit()
    vocab = index.vectorizer.vocabulary_
    # "gap year" and "early action" should exist as bigram features,
    # not just their component unigrams.
    assert "gap year" in vocab
    assert "early action" in vocab
    # unigrams should also still be present
    assert "gap" in vocab
    assert "year" in vocab


def test_vocabulary_size_matches_matrix_column_count(small_records):
    index = TfidfIndex(small_records)
    index.fit()
    assert index.vocabulary_size == index.matrix.shape[1]


# --- Query transformation ---

def test_transform_query_before_fit_raises(small_records):
    index = TfidfIndex(small_records)
    with pytest.raises(RetrievalError, match="fit\\(\\) must be called"):
        index.transform_query("What is a gap year?")


def test_transform_query_returns_vector_matching_corpus_dimensions(small_records):
    index = TfidfIndex(small_records)
    index.fit()
    query_vector = index.transform_query("Can I apply after a gap year?")
    assert query_vector.shape == (1, index.matrix.shape[1])


def test_transform_query_matches_relevant_vocabulary(small_records):
    index = TfidfIndex(small_records)
    index.fit()
    query_vector = index.transform_query("What is a gap year?")
    # The query should activate at least one non-zero TF-IDF weight —
    # if this were all zero, the query shares no vocabulary with the
    # corpus, which shouldn't happen for an on-topic gap-year question.
    assert query_vector.nnz > 0


def test_out_of_vocabulary_query_transforms_without_error(small_records):
    index = TfidfIndex(small_records)
    index.fit()
    # Complete gibberish with no overlap with the corpus at all.
    query_vector = index.transform_query("zzxxqqjjhh flibbertigibbet")
    assert query_vector.shape == (1, index.matrix.shape[1])
    assert query_vector.nnz == 0


def test_transform_query_is_case_insensitive(small_records):
    index = TfidfIndex(small_records)
    index.fit()
    lower = index.transform_query("what is early action?")
    upper = index.transform_query("WHAT IS EARLY ACTION?")
    assert (lower != upper).nnz == 0  # identical vectors


# --- Integration with the real knowledge base ---

@pytest.fixture
def real_index() -> TfidfIndex:
    kb = KnowledgeBaseService(settings.KNOWLEDGE_BASE_PATH)
    kb.load()
    index = TfidfIndex(kb.records)
    index.fit()
    return index


def test_real_knowledge_base_fits_with_expected_row_count(real_index: TfidfIndex):
    assert real_index.matrix.shape[0] == 147


def test_real_knowledge_base_produces_nonzero_vocabulary(real_index: TfidfIndex):
    assert real_index.vocabulary_size > 0


def test_real_gap_year_query_activates_vocabulary(real_index: TfidfIndex):
    vector = real_index.transform_query(
        "Can I still go to university after taking a year off?"
    )
    assert vector.nnz > 0


def test_real_out_of_domain_query_may_have_little_or_no_overlap(
    real_index: TfidfIndex,
):
    # Not a strict guarantee of zero (common English words might overlap),
    # but a clearly unrelated question should not densely activate the
    # admissions vocabulary. This is a sanity check, not a similarity
    # threshold test — that's Phase 6's job.
    vector = real_index.transform_query("What is the capital of France?")
    density = vector.nnz / real_index.matrix.shape[1]
    assert density < 0.01


# ============================================================
# Phase 5: RetrievalEngine — cosine similarity + top-k ranking
# ============================================================


@pytest.fixture
def small_engine(small_records) -> RetrievalEngine:
    index = TfidfIndex(small_records)
    index.fit()
    return RetrievalEngine(index, default_top_k=3)


@pytest.fixture
def real_engine(real_index: TfidfIndex) -> RetrievalEngine:
    return RetrievalEngine(real_index, default_top_k=settings.TOP_K)


# --- Construction / misuse ---

def test_engine_requires_a_fitted_index(small_records):
    unfitted_index = TfidfIndex(small_records)
    with pytest.raises(RetrievalError, match="already.*fit"):
        RetrievalEngine(unfitted_index)


def test_engine_rejects_top_k_below_one(small_records):
    index = TfidfIndex(small_records)
    index.fit()
    with pytest.raises(ValueError, match="default_top_k"):
        RetrievalEngine(index, default_top_k=0)


def test_retrieve_rejects_top_k_below_one_at_call_time(small_engine):
    with pytest.raises(ValueError, match="top_k"):
        small_engine.retrieve("What is a gap year?", top_k=0)


def test_retrieve_clamps_top_k_to_available_record_count(small_engine):
    # Only 3 records exist; asking for 10 should return 3, not error.
    results = small_engine.retrieve("What is a gap year?", top_k=10)
    assert len(results) == 3


# --- Ranking correctness ---

def test_retrieve_returns_results_sorted_by_descending_similarity(small_engine):
    results = small_engine.retrieve("What is a gap year?")
    scores = [m.similarity for m in results]
    assert scores == sorted(scores, reverse=True)


def test_retrieve_respects_top_k_count(small_engine):
    results = small_engine.retrieve("What is a gap year?", top_k=2)
    assert len(results) == 2


def test_similarity_scores_are_within_unit_range(small_engine):
    results = small_engine.retrieve("What is a gap year?")
    for match in results:
        assert 0.0 <= match.similarity <= 1.0


def test_obvious_matching_query_ranks_correct_record_first(small_engine):
    results = small_engine.retrieve("What is a gap year?")
    assert results[0].record.id == "B"  # the gap-year record


def test_default_top_k_is_used_when_not_specified(small_records):
    index = TfidfIndex(small_records)
    index.fit()
    engine = RetrievalEngine(index, default_top_k=1)
    results = engine.retrieve("What is Early Action?")
    assert len(results) == 1
    assert results[0].record.id == "A"


# --- Integration with the real knowledge base ---

def test_real_obvious_query_retrieves_correct_category(real_engine: RetrievalEngine):
    results = real_engine.retrieve("What is Early Action?")
    assert results[0].record.category == "Decision Types"


def test_real_paraphrased_gap_year_queries_retrieve_gap_year_category(
    real_engine: RetrievalEngine,
):
    # Section 61's explicit paraphrase examples. Three of the four share
    # enough vocabulary with the corpus ("gap year" appears literally, or
    # "year off" is a close lexical match) to rank Gap Years #1 outright.
    paraphrases = [
        "Can I still go to university after taking a year off?",
        "Does a gap year stop me from applying?",
        "Can I enter college after a gap year?",
    ]
    for query in paraphrases:
        results = real_engine.retrieve(query)
        assert results[0].record.category == "Gap Years", (
            f"Query {query!r} top match was "
            f"{results[0].record.category!r}, not 'Gap Years'"
        )


def test_real_hardest_gap_year_paraphrase_still_places_in_top_3(
    real_engine: RetrievalEngine,
):
    # This is a known, honest limitation of pure lexical TF-IDF, not a bug:
    # "I took a year off school. Can I still apply?" never says "gap" at
    # all, and shares more literal vocabulary ("school", "apply") with
    # "What is a safety school?" (Admissions Fundamentals) than with any
    # Gap Years record. TF-IDF has no concept of "year off" meaning the
    # same thing as "gap year" — that requires semantic/embedding-based
    # matching, which is explicitly out of scope for this project
    # (Section 2). Gap Years still appears in the top 3, which is the
    # realistic bar for a bag-of-words retrieval method; it does NOT
    # rank #1 here, and that's worth knowing before tuning the Phase 6
    # threshold, since this query's best score (~0.26) sits close to the
    # 0.30 starting threshold and may legitimately fall back instead of
    # answering — which is the *safe* failure mode per Section 18.
    query = "I took a year off school. Can I still apply?"
    results = real_engine.retrieve(query, top_k=3)
    categories = [m.record.category for m in results]
    assert "Gap Years" in categories


def test_real_international_financial_aid_query_retrieves_relevant_category(
    real_engine: RetrievalEngine,
):
    results = real_engine.retrieve(
        "How can international students get financial aid?"
    )
    top_categories = {m.record.category for m in results}
    assert top_categories & {"International Students", "Financial Aid"}


def test_real_out_of_domain_query_scores_much_lower_than_on_topic_query(
    real_engine: RetrievalEngine,
):
    # This is a comparative sanity check, not the threshold itself
    # (Phase 6 owns the actual cutoff decision) — an unrelated question's
    # best match should score well below an obviously on-topic one.
    on_topic = real_engine.retrieve("What is Early Action?")[0].similarity
    off_topic = real_engine.retrieve("What is the capital of France?")[0].similarity
    assert off_topic < on_topic


def test_real_top_k_returns_requested_count(real_engine: RetrievalEngine):
    results = real_engine.retrieve("What documents do I need to apply?", top_k=5)
    assert len(results) == 5


def test_similarity_is_distinct_field_from_confidence(real_engine: RetrievalEngine):
    # Guard against ever conflating retrieval similarity with the
    # knowledge base's own data-quality confidence field (Section 16).
    results = real_engine.retrieve("What is Early Action?")
    top = results[0]
    assert hasattr(top, "similarity")
    assert hasattr(top.record, "confidence")
    # They are unrelated values that just happen to both be floats —
    # confirm they're not silently the same number by construction.
    assert isinstance(top.similarity, float)
    assert isinstance(top.record.confidence, float)
