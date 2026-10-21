"""
Tests for app.services.chatbot.

Phase 6 (apply_threshold, select_related_questions, fallback suggestions):
threshold decisions against synthetic and real RetrievalMatch objects.

Phase 7 (validate_query, build_source_info, ChatbotService): full
query-to-response orchestration, tested against the real knowledge base.
"""

import pytest

from app.core.config import settings
from app.core.exceptions import InvalidQueryError
from app.models.schemas import FAQRecord
from app.services.chatbot import (
    FALLBACK_MESSAGE,
    ChatbotService,
    apply_threshold,
    build_source_info,
    humanize_question,
    select_related_questions,
    validate_query,
)
from app.services.knowledge_base import KnowledgeBaseService
from app.services.retrieval import RetrievalEngine, RetrievalMatch, TfidfIndex


def make_record(**overrides) -> FAQRecord:
    base = dict(
        id="TEST-001",
        category="Testing",
        canonical_question="What is the SAT?",
        alternative_user_questions=["Can you explain the SAT?"],
        answer="The SAT is a standardized test.",
        source_hierarchy=[],
        source_urls=[],
        information_type="stable",
        verification_date="2026-09-20",
        keywords=["sat"],
        confidence=0.95,
        update_rule="Review annually.",
        dynamic=False,
        requires_current_verification=False,
        follow_up_questions=[],
    )
    base.update(overrides)
    return FAQRecord(**base)


# --- apply_threshold: confident path ---

def test_high_similarity_match_is_confident():
    match = RetrievalMatch(record=make_record(), similarity=0.85)
    decision = apply_threshold([match], threshold=0.40)
    assert decision.is_confident is True
    assert decision.best_match is match
    assert decision.fallback_message is None


def test_confident_decision_populates_related_questions_from_other_matches():
    top = RetrievalMatch(
        record=make_record(id="A", canonical_question="What is the SAT?"),
        similarity=0.85,
    )
    second = RetrievalMatch(
        record=make_record(id="B", canonical_question="What is the ACT?"),
        similarity=0.60,
    )
    decision = apply_threshold([top, second], threshold=0.40)
    assert decision.is_confident is True
    assert "What is the ACT?" in decision.related_questions


# --- apply_threshold: fallback path ---

def test_low_similarity_match_triggers_fallback():
    match = RetrievalMatch(record=make_record(), similarity=0.10)
    decision = apply_threshold([match], threshold=0.40)
    assert decision.is_confident is False
    assert decision.best_match is None
    assert decision.fallback_message == FALLBACK_MESSAGE


def test_similarity_exactly_at_threshold_counts_as_confident():
    # Boundary check: >= threshold is confident, not > threshold.
    match = RetrievalMatch(record=make_record(), similarity=0.40)
    decision = apply_threshold([match], threshold=0.40)
    assert decision.is_confident is True


def test_similarity_just_below_threshold_falls_back():
    match = RetrievalMatch(record=make_record(), similarity=0.3999)
    decision = apply_threshold([match], threshold=0.40)
    assert decision.is_confident is False


def test_fallback_decision_still_surfaces_topic_suggestions():
    match = RetrievalMatch(
        record=make_record(canonical_question="What is the SAT?"),
        similarity=0.10,
    )
    decision = apply_threshold([match], threshold=0.40)
    assert "What is the SAT?" in decision.related_questions


def test_empty_matches_list_falls_back_without_crashing():
    decision = apply_threshold([], threshold=0.40)
    assert decision.is_confident is False
    assert decision.best_match is None
    assert decision.related_questions == []
    assert decision.fallback_message == FALLBACK_MESSAGE


def test_default_threshold_comes_from_settings():
    # No explicit threshold passed -> should use settings.SIMILARITY_THRESHOLD.
    just_below = settings.SIMILARITY_THRESHOLD - 0.01
    match = RetrievalMatch(record=make_record(), similarity=just_below)
    decision = apply_threshold([match])
    assert decision.is_confident is False


# --- select_related_questions ---
#
# Phase 10 correction: related questions now come ONLY from next-best
# retrieval matches' canonical_question, never from follow_up_questions
# (see the docstring in chatbot.py for why — every entry in that field
# across the real knowledge base turned out to be a boilerplate
# conversational prompt, not a standalone retrievable question).

def test_related_questions_come_from_next_best_matches():
    top = RetrievalMatch(record=make_record(id="A"), similarity=0.9)
    other = RetrievalMatch(
        record=make_record(id="B", canonical_question="Some other question?"),
        similarity=0.5,
    )
    related = select_related_questions([top, other], max_related=2)
    assert related == ["Some other question?"]


def test_related_questions_ignore_follow_up_questions_field():
    # Even if follow_up_questions is populated, it must not appear here.
    top = RetrievalMatch(
        record=make_record(
            follow_up_questions=["Can you show me the official source?"]
        ),
        similarity=0.9,
    )
    other = RetrievalMatch(
        record=make_record(id="B", canonical_question="Backup question?"),
        similarity=0.5,
    )
    related = select_related_questions([top, other], max_related=2)
    assert "Can you show me the official source?" not in related
    assert related == ["Backup question?"]


def test_related_questions_never_include_the_top_matchs_own_canonical_question():
    top = RetrievalMatch(
        record=make_record(canonical_question="What is the SAT?"),
        similarity=0.9,
    )
    duplicate = RetrievalMatch(
        record=make_record(id="B", canonical_question="What is the SAT?"),
        similarity=0.5,
    )
    related = select_related_questions([top, duplicate], max_related=3)
    assert "What is the SAT?" not in related


def test_related_questions_respects_max_related():
    top = RetrievalMatch(record=make_record(id="A"), similarity=0.9)
    others = [
        RetrievalMatch(
            record=make_record(id=str(i), canonical_question=f"Question {i}?"),
            similarity=0.5,
        )
        for i in range(4)
    ]
    related = select_related_questions([top, *others], max_related=2)
    assert len(related) == 2


def test_related_questions_empty_when_no_other_matches_exist():
    top = RetrievalMatch(record=make_record(id="A"), similarity=0.9)
    related = select_related_questions([top], max_related=3)
    assert related == []


# ============================================================
# Integration with the real knowledge base + evidence-based
# threshold (Section 40)
# ============================================================


@pytest.fixture
def real_engine() -> RetrievalEngine:
    kb = KnowledgeBaseService(settings.KNOWLEDGE_BASE_PATH)
    kb.load()
    index = TfidfIndex(kb.records)
    index.fit()
    return RetrievalEngine(index, default_top_k=3)


# On-domain queries that should be answered confidently at the default
# threshold (0.40) — high-signal questions from Section 60's demo flow.
CONFIDENT_QUERIES = [
    ("What is Early Action?", "Decision Types"),
    ("Can international students receive financial aid?", "International Students"),
    ("What is a gap year?", "Gap Years"),
]

# Off-domain queries that must fall back at the default threshold. These
# are exactly the queries that exposed the FAQ-037 duplication artifact
# and drove the 0.30 -> 0.40 threshold change documented in config.py.
FALLBACK_QUERIES = [
    "What is the capital of France?",
    "Who won the World Cup?",
    "Write me a Python game.",
    "What is Bitcoin?",
    "What is the weather today?",
    "Tell me a joke.",
]


@pytest.mark.parametrize("query,expected_category", CONFIDENT_QUERIES)
def test_real_on_domain_queries_are_answered_confidently(
    real_engine: RetrievalEngine, query, expected_category
):
    matches = real_engine.retrieve(query)
    decision = apply_threshold(matches)
    assert decision.is_confident is True
    assert decision.best_match.record.category == expected_category


@pytest.mark.parametrize("query", FALLBACK_QUERIES)
def test_real_off_domain_queries_fall_back(real_engine: RetrievalEngine, query):
    matches = real_engine.retrieve(query)
    decision = apply_threshold(matches)
    assert decision.is_confident is False
    assert decision.fallback_message == FALLBACK_MESSAGE
    # A fallback still gives the user somewhere to go — never an empty dead end.
    assert len(decision.related_questions) > 0


def test_real_confident_answer_exposes_related_questions(real_engine: RetrievalEngine):
    matches = real_engine.retrieve("What is Early Action?")
    decision = apply_threshold(matches)
    assert decision.is_confident is True
    assert len(decision.related_questions) > 0
    # None of the related questions should just repeat the answer itself.
    assert decision.best_match.record.canonical_question not in decision.related_questions


def test_real_related_questions_never_lead_to_a_dead_end(real_engine: RetrievalEngine):
    # The Phase 10 guarantee this whole fix exists for: clicking ANY
    # related question shown after a confident answer must itself
    # resolve confidently, never fall back. This was NOT true before the
    # fix — follow_up_questions entries like "Can you show me the
    # official source?" produced fallbacks when clicked, since they were
    # never real FAQ topics in the corpus.
    seed_queries = [
        "What is Early Action?",
        "What is a gap year?",
        "What is the SAT?",
        "What is the CSS Profile?",
    ]
    for seed in seed_queries:
        decision = apply_threshold(real_engine.retrieve(seed))
        assert decision.is_confident is True
        for related_question in decision.related_questions:
            follow_up_decision = apply_threshold(real_engine.retrieve(related_question))
            assert follow_up_decision.is_confident is True, (
                f"Related question {related_question!r} (shown after "
                f"answering {seed!r}) led to a fallback dead end."
            )


# ============================================================
# Phase 7: validate_query, build_source_info, ChatbotService
# ============================================================


# --- validate_query ---

def test_validate_query_accepts_normal_string():
    assert validate_query("What is Early Action?", max_length=500) == "What is Early Action?"


def test_validate_query_rejects_empty_string():
    with pytest.raises(InvalidQueryError, match="empty"):
        validate_query("", max_length=500)


def test_validate_query_rejects_whitespace_only_string():
    with pytest.raises(InvalidQueryError, match="empty"):
        validate_query("     ", max_length=500)


def test_validate_query_rejects_too_long_string():
    with pytest.raises(InvalidQueryError, match="maximum length"):
        validate_query("a" * 501, max_length=500)


def test_validate_query_accepts_string_at_exact_max_length():
    query = "a" * 500
    assert validate_query(query, max_length=500) == query


def test_validate_query_rejects_non_string_input():
    with pytest.raises(InvalidQueryError, match="must be a string"):
        validate_query(12345, max_length=500)  # type: ignore[arg-type]


def test_validate_query_rejects_none():
    with pytest.raises(InvalidQueryError, match="must be a string"):
        validate_query(None, max_length=500)  # type: ignore[arg-type]


def test_validate_query_uses_settings_default_when_max_length_omitted():
    too_long = "a" * (settings.MAX_QUERY_LENGTH + 1)
    with pytest.raises(InvalidQueryError, match="maximum length"):
        validate_query(too_long)


# --- build_source_info ---

def test_build_source_info_returns_none_for_record_without_sources():
    record = make_record(source_hierarchy=[], source_urls=[])
    assert build_source_info(record) is None


def test_build_source_info_uses_rank_one_source():
    from app.models.schemas import SourceHierarchyEntry

    record = make_record(
        source_hierarchy=[
            SourceHierarchyEntry(rank=1, source_type="primary", source_name="Top Source"),
            SourceHierarchyEntry(rank=2, source_type="primary", source_name="Second Source"),
        ],
        source_urls=["https://top.example.com", "https://second.example.com"],
    )
    source = build_source_info(record)
    assert source.name == "Top Source"
    assert source.url == "https://top.example.com"


def test_build_source_info_hides_unresolved_sentinel_url():
    from app.models.schemas import SourceHierarchyEntry

    record = make_record(
        source_hierarchy=[
            SourceHierarchyEntry(
                rank=1, source_type="primary", source_name="The college's official site"
            ),
        ],
        source_urls=["COLLEGE_OFFICIAL_SOURCE_REQUIRED"],
    )
    source = build_source_info(record)
    assert source.name == "The college's official site"
    assert source.url is None


def test_build_source_info_real_dyn_record_has_no_link(real_kb: KnowledgeBaseService):
    dyn_record = real_kb.get_by_category("Dynamic College Information")[0]
    source = build_source_info(dyn_record)
    assert source is not None
    assert source.url is None


def test_build_source_info_real_stable_record_has_a_real_link(real_kb: KnowledgeBaseService):
    record = real_kb.get_by_id("FAQ-001")
    source = build_source_info(record)
    assert source is not None
    assert source.url is not None
    assert source.url.startswith("https://")


# --- ChatbotService ---

@pytest.fixture
def real_kb() -> KnowledgeBaseService:
    kb = KnowledgeBaseService(settings.KNOWLEDGE_BASE_PATH)
    kb.load()
    return kb


@pytest.fixture
def chatbot_service(real_engine: RetrievalEngine) -> ChatbotService:
    return ChatbotService(real_engine)


def test_answer_query_confident_response_shape(chatbot_service: ChatbotService):
    response = chatbot_service.answer_query("What is Early Action?")
    assert response.fallback is False
    assert response.category == "Decision Types"
    assert response.matched_question is not None
    assert response.similarity_score is not None
    assert response.source is not None
    assert response.verification_date is not None
    assert response.requires_current_verification is False


def test_answer_query_fallback_response_shape(chatbot_service: ChatbotService):
    response = chatbot_service.answer_query("What is the capital of France?")
    assert response.fallback is True
    assert response.matched_question is None
    assert response.category is None
    assert response.similarity_score is None
    assert response.source is None
    assert len(response.related_questions) > 0
    assert "not confident" in response.answer.lower()


def test_answer_query_flags_dynamic_records_for_verification(
    chatbot_service: ChatbotService,
):
    response = chatbot_service.answer_query(
        "What is the current application deadline for Harvard?"
    )
    # This should hit a Dynamic College Information record and never
    # invent a specific deadline (Section 24).
    assert response.fallback is False
    assert response.requires_current_verification is True
    assert response.category == "Dynamic College Information"


def test_answer_query_does_not_mutate_dynamic_answer_text(
    chatbot_service: ChatbotService, real_kb: KnowledgeBaseService
):
    # The knowledge base's own wording for dynamic records is already
    # cautious — confirm we pass it through unmodified rather than
    # appending a redundant notice on top of it.
    response = chatbot_service.answer_query(
        "What is the current application deadline for Harvard?"
    )
    matching_record = next(
        r
        for r in real_kb.get_by_category("Dynamic College Information")
        if r.answer == response.answer
    )
    assert response.answer == matching_record.answer


# --- humanize_question (Phase 13: found via live user testing) ---

def test_humanize_question_replaces_college_placeholder():
    assert (
        humanize_question("What is [COLLEGE]'s current acceptance rate?")
        == "What is a college's current acceptance rate?"
    )


def test_humanize_question_replaces_entry_year_placeholder():
    assert (
        humanize_question("Is [COLLEGE] test-optional for [ENTRY YEAR]?")
        == "Is a college test-optional for a given year?"
    )


def test_humanize_question_leaves_normal_text_unchanged():
    assert humanize_question("What is Early Action?") == "What is Early Action?"


def test_answer_query_matched_question_never_leaks_placeholder_brackets(
    chatbot_service: ChatbotService,
):
    response = chatbot_service.answer_query(
        "What is the current application deadline for Harvard?"
    )
    assert response.matched_question is not None
    assert "[" not in response.matched_question
    assert "]" not in response.matched_question


def test_related_questions_never_leak_placeholder_brackets(
    chatbot_service: ChatbotService,
):
    # Ask something that ranks a Dynamic College Information record
    # among the related-question candidates, and confirm no raw
    # bracket placeholder ever reaches the user — this was a real bug
    # caught via a live user testing session (Phase 13), not caught by
    # the earlier automated tests since they didn't check this specific
    # rendering detail.
    seed_queries = [
        "What is Early Action?",
        "What documents do I need?",
        "What is Harvard's current acceptance rate?",
    ]
    for seed in seed_queries:
        response = chatbot_service.answer_query(seed)
        for question in response.related_questions:
            assert "[" not in question and "]" not in question, (
                f"Related question {question!r} (from seed {seed!r}) "
                f"leaked a raw placeholder bracket."
            )


def test_answer_query_raises_invalid_query_error_on_empty_input(
    chatbot_service: ChatbotService,
):
    with pytest.raises(InvalidQueryError):
        chatbot_service.answer_query("")


def test_answer_query_raises_invalid_query_error_on_too_long_input(
    chatbot_service: ChatbotService,
):
    with pytest.raises(InvalidQueryError):
        chatbot_service.answer_query("a" * (settings.MAX_QUERY_LENGTH + 1))


def test_answer_query_stable_record_never_flagged_for_verification(
    chatbot_service: ChatbotService,
):
    # FAQ-001 is explicitly information_type="stable" in the real
    # knowledge base — a genuinely settled definition, not something
    # that varies by college policy or admission cycle. (Note: "What is
    # a gap year?" was NOT used for this test — despite being a plain
    # definition, the KB deliberately marks it policy_dependent because
    # how a gap year affects admissions varies by institution, which is
    # a legitimate design choice on the data's part, not a bug.)
    response = chatbot_service.answer_query("What is college admission?")
    assert response.fallback is False
    assert response.category == "Admissions Fundamentals"
    assert response.requires_current_verification is False
