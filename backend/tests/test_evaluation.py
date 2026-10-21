"""
Section 39: formal retrieval evaluation against a 40-query set covering
every category (tests/fixtures/evaluation_queries.py), run at the
production SIMILARITY_THRESHOLD (0.40, set in Phase 6).

This is NOT the same thing as test_retrieval.py / test_chatbot.py's
targeted unit tests — those check specific mechanisms in isolation
(ranking order, threshold boundaries, etc.). This file measures overall
system behavior against a broad, representative query set and reports
real numbers, per Section 39's explicit instruction not to claim
accuracy without measuring it.

Three outcomes are tracked separately for on-domain queries, because
they are NOT equally bad:
  - correct          : confident AND right category (the goal)
  - wrong_confident   : confident AND WRONG category (Section 18's worst
                        case — a confidently wrong answer)
  - declined          : fell back when an answer existed (safe, if
                        unhelpful)
A "not correct" result that's a safe decline is a much smaller problem
than one that's wrong-but-confident, so the assertions below bound the
dangerous failure mode much more tightly than the unhelpful one.

Baseline measured during Phase 11 (this run): 26 on-domain queries ->
65% correct, 8% (2 queries) wrong-confident, 27% safely declined; 22/26
(85%) had the right category somewhere in the top 3. 14 off-domain
queries -> 100% correctly declined. The two wrong-confident cases are
documented below — both are genuine, explicable TF-IDF limitations
(lexical overlap with an adjacent category's vocabulary), not code bugs:

  1. "How do I decide which colleges to apply to?" matches "How do I
     apply to a U.S. college?" (Application Process, sim 0.567) instead
     of College Selection's "How should I choose colleges?" — the query
     shares "apply"/"colleges" with Application Process's canonical
     question far more than it shares "choose"/"compare" with College
     Selection's.
  2. "Where can I check if a college's cost of attendance changed?"
     matches the definitional "What is cost of attendance?" (Financial
     Aid, sim 0.645) ahead of the DYN record for a college's CURRENT
     cost of attendance (sim 0.543) — the literal phrase "cost of
     attendance" overlaps more with the definition than "changed"/
     "current" overlaps with the dynamic record's wording.

Both would need semantic/embedding-based matching to fix reliably,
which is explicitly out of scope for this project (Section 2). The
thresholds asserted below reflect this measured baseline, not an
aspirational number — if the corpus or threshold changes, re-run this
file with `pytest -s` to see the new baseline before adjusting these
bounds.
"""

import pytest

from app.core.config import settings
from app.services.chatbot import apply_threshold
from app.services.knowledge_base import KnowledgeBaseService
from app.services.retrieval import RetrievalEngine, TfidfIndex
from tests.fixtures.evaluation_queries import EVALUATION_QUERIES


@pytest.fixture(scope="module")
def engine() -> RetrievalEngine:
    kb = KnowledgeBaseService(settings.KNOWLEDGE_BASE_PATH)
    kb.load()
    index = TfidfIndex(kb.records)
    index.fit()
    return RetrievalEngine(index, default_top_k=3)


@pytest.fixture(scope="module")
def evaluation_results(engine: RetrievalEngine):
    """Run every fixture query once per test session and return the raw
    per-query outcomes, so every test in this file scores the SAME run
    rather than each re-running retrieval independently."""
    results = []
    for item in EVALUATION_QUERIES:
        matches = engine.retrieve(item["query"], top_k=3)
        decision = apply_threshold(matches)
        results.append({"item": item, "matches": matches, "decision": decision})
    return results


def _confident_subset(evaluation_results):
    return [r for r in evaluation_results if r["item"]["expect"] == "confident"]


def _fallback_subset(evaluation_results):
    return [r for r in evaluation_results if r["item"]["expect"] == "fallback"]


def test_evaluation_set_has_at_least_thirty_queries():
    # Section 39's explicit ask: 30-50 representative queries.
    assert len(EVALUATION_QUERIES) >= 30


def test_evaluation_set_covers_every_category():
    categories_in_set = {
        item["expected_category"]
        for item in EVALUATION_QUERIES
        if item["expect"] == "confident"
    }
    from app.services.knowledge_base import KnowledgeBaseService as KB

    kb = KB(settings.KNOWLEDGE_BASE_PATH)
    kb.load()
    assert categories_in_set == set(kb.categories)


def test_top1_accuracy_meets_measured_baseline(evaluation_results):
    confident = _confident_subset(evaluation_results)
    correct = sum(
        1
        for r in confident
        if r["decision"].is_confident
        and r["decision"].best_match.record.category == r["item"]["expected_category"]
    )
    accuracy = correct / len(confident)
    # Measured baseline: 65%. Floor set a little below to tolerate minor
    # fluctuation without masking a real regression.
    assert accuracy >= 0.55, f"Top-1 accuracy dropped to {accuracy:.0%}"


def test_top3_hit_rate_meets_measured_baseline(evaluation_results):
    confident = _confident_subset(evaluation_results)
    hits = sum(
        1
        for r in confident
        if r["item"]["expected_category"]
        in {m.record.category for m in r["matches"]}
    )
    rate = hits / len(confident)
    # Measured baseline: 85%.
    assert rate >= 0.75, f"Top-3 hit rate dropped to {rate:.0%}"


def test_wrong_confident_rate_stays_low(evaluation_results):
    """
    The dangerous failure mode (Section 18): confidently answering with
    the WRONG category. Measured baseline: 2/26 (8%). This is bounded
    much more tightly than overall accuracy, because a wrong-but-
    confident answer is worse than an unhelpful decline.
    """
    confident = _confident_subset(evaluation_results)
    wrong_confident = sum(
        1
        for r in confident
        if r["decision"].is_confident
        and r["decision"].best_match.record.category != r["item"]["expected_category"]
    )
    rate = wrong_confident / len(confident)
    assert rate <= 0.15, f"Wrong-confident rate rose to {rate:.0%}"


def test_off_domain_queries_all_correctly_fall_back(evaluation_results):
    """Measured baseline: 14/14 (100%). Every off-domain / nonsense
    query in the set must be declined, never confidently answered."""
    fallback = _fallback_subset(evaluation_results)
    correctly_declined = sum(1 for r in fallback if not r["decision"].is_confident)
    assert correctly_declined == len(fallback)


def test_print_full_evaluation_report(evaluation_results, capsys):
    """Not a pass/fail check — prints the full per-query report (run with
    `pytest tests/test_evaluation.py -s` to see it) so a human reviewing
    the project can see exactly which queries succeed, decline, or
    mismatch, not just aggregate percentages."""
    lines = [f"\n{'OUTCOME':18} {'QUERY':55} {'EXPECTED':26} {'SIMILARITY'}"]
    for r in evaluation_results:
        item, decision, matches = r["item"], r["decision"], r["matches"]
        sim = matches[0].similarity if matches else 0.0
        if item["expect"] == "confident":
            if not decision.is_confident:
                outcome = "DECLINED"
            elif decision.best_match.record.category == item["expected_category"]:
                outcome = "CORRECT"
            else:
                outcome = "WRONG-CONFIDENT"
            expected = item["expected_category"]
        else:
            outcome = "CORRECT" if not decision.is_confident else "FALSE-POSITIVE"
            expected = "(fallback)"
        lines.append(f"{outcome:18} {item['query'][:53]:55} {expected[:24]:26} {sim:.3f}")
    print("\n".join(lines))
