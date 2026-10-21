"""
Chatbot service.

Built incrementally across Phases 6-7:

Phase 6 (apply_threshold, select_related_questions, _fallback_suggestions):
decides whether a set of ranked retrieval matches is trustworthy enough
to answer with, and what related questions to surface either way.

Phase 7 (this addition — ChatbotService, validate_query, build_source_info):
wires everything together into the full pipeline Section 20 describes:

    validate_query
      -> preprocess + retrieve (delegated to RetrievalEngine)
      -> apply_threshold
      -> format_answer / fallback response
      -> ChatResponse

This is the one place that turns "a ranked FAQ match" into "a finished
API response" — the FastAPI route (Phase 8) should be a thin wrapper
around ChatbotService.answer_query() and nothing more.
"""

from dataclasses import dataclass

from app.core.config import settings
from app.core.exceptions import InvalidQueryError
from app.core.logging import logger
from app.models.schemas import ChatResponse, FAQRecord, SourceInfo
from app.services.retrieval import RetrievalEngine, RetrievalMatch

# Section 18's suggested wording. Kept as a constant rather than
# generated dynamically — a fallback should be a stable, predictable
# message, not something that varies per query.
FALLBACK_MESSAGE = (
    "I'm not confident that I found the right answer for that question. "
    "Try asking it another way, or choose one of the topics below."
)

DEFAULT_MAX_RELATED_QUESTIONS = 3

# Dynamic College Information records use bracket placeholders in their
# canonical_question/alternative_user_questions ([COLLEGE], [ENTRY YEAR])
# since they represent a template applicable to any college/year, not
# one fixed question — correct for the source data, but a live user
# test in Phase 13 showed the raw brackets leaking straight into the UI
# as a "related question" ("What is [COLLEGE]'s current acceptance
# rate?"), which reads as a template leak rather than a real, clickable
# question. This is a display-only transform, applied wherever a
# canonical_question is exposed to the user — never to `answer` text
# (which never contains these placeholders in the real data) and never
# before retrieval matching (which has already happened by this point).
_PLACEHOLDER_REPLACEMENTS = {
    "[COLLEGE]": "a college",
    "[ENTRY YEAR]": "a given year",
}


def humanize_question(question: str) -> str:
    """Replace template placeholders with natural phrasing for display."""
    for token, replacement in _PLACEHOLDER_REPLACEMENTS.items():
        question = question.replace(token, replacement)
    return question


@dataclass(frozen=True)
class AnswerDecision:
    """
    The result of applying the similarity threshold to a set of ranked
    retrieval matches.

    - is_confident=True  -> best_match is set, fallback_message is None.
    - is_confident=False -> best_match is None, fallback_message is set.

    related_questions is populated in both cases, but sourced
    differently (see select_related_questions / _fallback_suggestions).
    """

    is_confident: bool
    best_match: RetrievalMatch | None
    related_questions: list[str]
    fallback_message: str | None


def apply_threshold(
    matches: list[RetrievalMatch],
    threshold: float | None = None,
    max_related: int = DEFAULT_MAX_RELATED_QUESTIONS,
) -> AnswerDecision:
    """
    Section 17/18: if the top match's similarity is below `threshold`,
    do NOT force an answer — return a fallback decision instead.

    threshold defaults to settings.SIMILARITY_THRESHOLD so it stays a
    config value (Section 50), but can be overridden per-call, which is
    what makes threshold-sweep evaluation (Section 40) possible without
    restarting the app.
    """
    threshold = settings.SIMILARITY_THRESHOLD if threshold is None else threshold

    if not matches:
        # Defensive: RetrievalEngine.retrieve() should never return an
        # empty list against a non-empty knowledge base (top_k is
        # clamped to at least 1 record), but this guards against an
        # IndexError below rather than trusting that invariant blindly.
        logger.warning("apply_threshold called with an empty matches list.")
        return AnswerDecision(
            is_confident=False,
            best_match=None,
            related_questions=[],
            fallback_message=FALLBACK_MESSAGE,
        )

    top = matches[0]

    if top.similarity < threshold:
        logger.info(
            f"Fallback triggered: top similarity {top.similarity:.4f} "
            f"below threshold {threshold}."
        )
        return AnswerDecision(
            is_confident=False,
            best_match=None,
            related_questions=_fallback_suggestions(matches, max_related),
            fallback_message=FALLBACK_MESSAGE,
        )

    return AnswerDecision(
        is_confident=True,
        best_match=top,
        related_questions=select_related_questions(matches, max_related),
        fallback_message=None,
    )


def select_related_questions(
    matches: list[RetrievalMatch],
    max_related: int = DEFAULT_MAX_RELATED_QUESTIONS,
) -> list[str]:
    """
    Build the "You may also want to ask" list (Section 32) for a
    CONFIDENT answer.

    Sourced ONLY from the canonical_question of the next-best retrieval
    matches — deliberately NOT from the record's own `follow_up_questions`
    field. This is a correction made during Phase 10 integration testing:
    clicking a real follow_up_questions entry through the full frontend
    ->backend chain produced a fallback dead end. Inspecting the whole
    knowledge base showed why — every single one of the 306
    follow_up_questions entries across all 147 records is one of two
    boilerplate templates ("Can you show me the official source?" / "What
    should I check next?" for regular FAQs; a 3-question slot-filling set
    — "What is your intended entry year?", "Are you applying as an
    international student?", "Would you like the official source?" — for
    the DYN-### records). These read as prompts for a stateful,
    slot-filling dialogue manager, not as standalone questions this
    TF-IDF retrieval system can answer on their own; building that kind
    of conversational state machine is out of scope here (Section 64).
    A next-best match's canonical_question, by contrast, is guaranteed to
    retrieve confidently if clicked — it's a literal, verbatim entry in
    that record's own retrieval text, so querying it again reproduces
    close to a perfect match against itself.
    """
    top = matches[0]
    related: list[str] = []
    top_question = humanize_question(top.record.canonical_question)

    if len(related) < max_related:
        for match in matches[1:]:
            if len(related) >= max_related:
                break
            question = humanize_question(match.record.canonical_question)
            if question not in related and question != top_question:
                related.append(question)

    return related[:max_related]


def _fallback_suggestions(
    matches: list[RetrievalMatch],
    max_related: int = DEFAULT_MAX_RELATED_QUESTIONS,
) -> list[str]:
    """
    Build the "choose one of the topics below" suggestions (Section 18)
    for a FALLBACK response.

    Unlike the confident case, there is no trustworthy "best match" to
    pull curated follow-ups from — every candidate scored below the
    confidence threshold. Instead, surface the canonical questions of the
    nearest (even if not confident) matches as clickable starting points.
    This is explicitly framed to the user as "topics you might want to
    explore," never as an answer, so showing a near-miss here doesn't
    contradict the fallback message above it.
    """
    seen: set[str] = set()
    suggestions: list[str] = []
    for match in matches:
        question = humanize_question(match.record.canonical_question)
        if question not in seen:
            suggestions.append(question)
            seen.add(question)
        if len(suggestions) >= max_related:
            break
    return suggestions


# ============================================================
# Phase 7: query validation, source formatting, full orchestration
# ============================================================


def validate_query(raw_query: object, max_length: int | None = None) -> str:
    """
    Section 26/37: validate a raw user query before it touches
    preprocessing or retrieval.

    Rejects: non-string input, empty/whitespace-only input, and input
    longer than max_length. Returns the original (un-stripped) string on
    success — preprocessing, not validation, owns normalization.
    """
    max_length = settings.MAX_QUERY_LENGTH if max_length is None else max_length

    if not isinstance(raw_query, str):
        raise InvalidQueryError(
            f"Query must be a string, got {type(raw_query).__name__}."
        )

    if not raw_query.strip():
        raise InvalidQueryError("Query cannot be empty.")

    if len(raw_query) > max_length:
        raise InvalidQueryError(
            f"Query exceeds the maximum length of {max_length} characters "
            f"(got {len(raw_query)})."
        )

    return raw_query


def build_source_info(record: FAQRecord) -> SourceInfo | None:
    """
    Section 21/22: expose the record's most authoritative source.

    source_hierarchy and source_urls are parallel arrays (verified
    against the real knowledge base — every record's two lists are the
    same length and already sorted by ascending rank), so the rank-1
    entry and the first URL correspond to the same source. If that URL
    is the unresolved-source sentinel (Dynamic College Information
    records — Section 23), `url` is left as None rather than exposing a
    placeholder string as if it were a real link.
    """
    if not record.source_hierarchy:
        return None

    top_source = record.source_hierarchy[0]
    top_url = record.source_urls[0] if record.source_urls else None
    if top_url is not None and top_url not in record.resolved_source_urls:
        # It matched the unresolved sentinel — don't expose it as a link.
        top_url = None

    return SourceInfo(name=top_source.source_name, url=top_url)


class ChatbotService:
    """
    Orchestrates the full answer pipeline (Section 20):

        validate_query -> RetrievalEngine.retrieve -> apply_threshold
        -> ChatResponse

    Preprocessing itself happens inside RetrievalEngine/TfidfIndex
    (Section 12 requires it applied consistently to both queries and
    corpus text, which is already guaranteed there) — this class doesn't
    call it a second time.
    """

    def __init__(
        self,
        retrieval_engine: RetrievalEngine,
        max_query_length: int | None = None,
        similarity_threshold: float | None = None,
        top_k: int | None = None,
    ):
        self._engine = retrieval_engine
        self._max_query_length = max_query_length
        self._similarity_threshold = similarity_threshold
        self._top_k = top_k

    def answer_query(self, raw_query: str) -> ChatResponse:
        query = validate_query(raw_query, self._max_query_length)

        matches = self._engine.retrieve(query, top_k=self._top_k)
        decision = apply_threshold(matches, threshold=self._similarity_threshold)

        if not decision.is_confident:
            return ChatResponse(
                answer=decision.fallback_message,
                fallback=True,
                requires_current_verification=False,
                related_questions=decision.related_questions,
            )

        match = decision.best_match
        record = match.record

        # Section 23/24: never silently treat dynamic/policy-dependent
        # content as settled fact. The knowledge base's own answer text
        # for these records is already written cautiously (e.g. "Verify
        # the deadline on the college's official admissions page..." —
        # it never states a specific date), so we deliberately do NOT
        # mutate or append to `answer` here. Appending a generic notice
        # on top would risk duplicating wording the record already has,
        # or clashing with it. Instead we surface the flag on the
        # response so the frontend can render a distinct "verify this"
        # treatment without altering the vetted answer text itself.
        requires_verification = record.dynamic or record.requires_current_verification

        logger.info(
            f"Answered query with record {record.id} "
            f"(similarity={match.similarity:.4f}, "
            f"requires_verification={requires_verification})."
        )

        return ChatResponse(
            answer=record.answer,
            matched_question=humanize_question(record.canonical_question),
            category=record.category,
            similarity_score=match.similarity,
            source=build_source_info(record),
            verification_date=record.verification_date,
            related_questions=decision.related_questions,
            fallback=False,
            requires_current_verification=requires_verification,
        )
