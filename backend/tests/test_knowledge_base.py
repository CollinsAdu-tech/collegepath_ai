"""
Tests for KnowledgeBaseService (Section 38 — Knowledge base tests).

Covers:
- the real knowledge base loads correctly and reports the right count
- required fields exist on every loaded record
- categories exist and match what the file declares
- malformed records are detected and raise KnowledgeBaseLoadError
"""

import json

import pytest

from app.core.config import settings
from app.core.exceptions import KnowledgeBaseLoadError
from app.services.knowledge_base import KnowledgeBaseService


@pytest.fixture
def loaded_kb() -> KnowledgeBaseService:
    """The real, shipped knowledge base, loaded fresh for each test."""
    kb = KnowledgeBaseService(settings.KNOWLEDGE_BASE_PATH)
    kb.load()
    return kb


def test_real_knowledge_base_loads(loaded_kb: KnowledgeBaseService):
    assert loaded_kb.is_loaded
    assert len(loaded_kb.records) == 147


def test_categories_match_declared_categories(loaded_kb: KnowledgeBaseService):
    expected = {
        "Admissions Fundamentals",
        "After Admission",
        "Application Process",
        "Application Requirements",
        "Application Strategy",
        "College Selection",
        "Decision Types",
        "Dynamic College Information",
        "Essays & Recommendations",
        "Financial Aid",
        "Full Funding",
        "Gap Years",
        "International Students",
        "Safety & Verification",
        "Scholarships & Funding",
        "Testing",
    }
    assert set(loaded_kb.categories) == expected
    assert len(loaded_kb.categories) == 16


def test_every_record_used_a_declared_category(loaded_kb: KnowledgeBaseService):
    declared = set(loaded_kb.categories)
    used = {r.category for r in loaded_kb.records}
    assert used.issubset(declared)


def test_required_fields_present_on_every_record(loaded_kb: KnowledgeBaseService):
    required_fields = [
        "id", "category", "canonical_question", "alternative_user_questions",
        "answer", "source_hierarchy", "source_urls", "information_type",
        "verification_date", "keywords", "confidence", "update_rule",
        "dynamic", "requires_current_verification",
    ]
    for record in loaded_kb.records:
        for field in required_fields:
            assert hasattr(record, field), f"{record.id} missing field {field}"


def test_confidence_scores_in_valid_range(loaded_kb: KnowledgeBaseService):
    for record in loaded_kb.records:
        assert 0.0 <= record.confidence <= 1.0


def test_get_by_id_returns_expected_record(loaded_kb: KnowledgeBaseService):
    record = loaded_kb.get_by_id("FAQ-001")
    assert record is not None
    assert record.canonical_question == "What is college admission?"


def test_get_by_id_returns_none_for_unknown_id(loaded_kb: KnowledgeBaseService):
    assert loaded_kb.get_by_id("FAQ-99999") is None


def test_get_by_category_returns_only_matching_records(loaded_kb: KnowledgeBaseService):
    gap_year_records = loaded_kb.get_by_category("Gap Years")
    assert len(gap_year_records) == 9
    assert all(r.category == "Gap Years" for r in gap_year_records)


def test_dynamic_records_flagged_correctly(loaded_kb: KnowledgeBaseService):
    dynamic_records = [r for r in loaded_kb.records if r.dynamic]
    assert len(dynamic_records) == 75
    assert all(r.requires_current_verification for r in dynamic_records)


def test_dyn_records_expose_unresolved_source_sentinel(loaded_kb: KnowledgeBaseService):
    """The 12 DYN-### records use a placeholder instead of a real URL —
    confirm the model surfaces this so the response layer can avoid
    rendering it as a clickable link."""
    dyn_records = loaded_kb.get_by_category("Dynamic College Information")
    assert len(dyn_records) == 12
    assert all(r.has_unresolved_sources for r in dyn_records)
    for r in dyn_records:
        assert r.resolved_source_urls == [] or all(
            u != "COLLEGE_OFFICIAL_SOURCE_REQUIRED" for u in r.resolved_source_urls
        )


# --- Failure-path tests using deliberately broken files ---

def test_missing_file_raises_knowledge_base_load_error(tmp_path):
    missing_path = tmp_path / "does_not_exist.json"
    kb = KnowledgeBaseService(missing_path)
    with pytest.raises(KnowledgeBaseLoadError, match="not found"):
        kb.load()


def test_invalid_json_raises_knowledge_base_load_error(tmp_path):
    bad_file = tmp_path / "broken.json"
    bad_file.write_text("{ this is not valid json ]", encoding="utf-8")
    kb = KnowledgeBaseService(bad_file)
    with pytest.raises(KnowledgeBaseLoadError, match="not valid JSON"):
        kb.load()


def test_missing_required_field_raises_knowledge_base_load_error(tmp_path):
    # Take one real record, delete a required field, and confirm the
    # loader rejects the whole document rather than silently accepting
    # a partial record.
    with open(settings.KNOWLEDGE_BASE_PATH, encoding="utf-8") as f:
        data = json.load(f)

    del data["faq_records"][0]["confidence"]

    bad_file = tmp_path / "missing_field.json"
    bad_file.write_text(json.dumps(data), encoding="utf-8")

    kb = KnowledgeBaseService(bad_file)
    with pytest.raises(KnowledgeBaseLoadError, match="schema validation"):
        kb.load()


def test_duplicate_ids_raise_knowledge_base_load_error(tmp_path):
    with open(settings.KNOWLEDGE_BASE_PATH, encoding="utf-8") as f:
        data = json.load(f)

    # Force a duplicate id.
    data["faq_records"][1]["id"] = data["faq_records"][0]["id"]

    bad_file = tmp_path / "duplicate_ids.json"
    bad_file.write_text(json.dumps(data), encoding="utf-8")

    kb = KnowledgeBaseService(bad_file)
    with pytest.raises(KnowledgeBaseLoadError, match="Duplicate FAQ record id"):
        kb.load()


def test_empty_faq_records_raises_knowledge_base_load_error(tmp_path):
    with open(settings.KNOWLEDGE_BASE_PATH, encoding="utf-8") as f:
        data = json.load(f)

    data["faq_records"] = []

    bad_file = tmp_path / "empty_records.json"
    bad_file.write_text(json.dumps(data), encoding="utf-8")

    kb = KnowledgeBaseService(bad_file)
    with pytest.raises(KnowledgeBaseLoadError, match="zero faq_records"):
        kb.load()


def test_accessing_unloaded_kb_raises(tmp_path):
    kb = KnowledgeBaseService(settings.KNOWLEDGE_BASE_PATH)
    with pytest.raises(KnowledgeBaseLoadError, match="before load"):
        _ = kb.records
