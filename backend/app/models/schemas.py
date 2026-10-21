"""
Pydantic models for CollegePath AI.

This file has two jobs:

1. Validate the shape of the knowledge-base JSON as we load it
   (SourceHierarchyEntry, FAQRecord, KnowledgeBaseDocument).
2. Define the API's request/response contracts (added in later phases,
   e.g. ChatRequest/ChatResponse in Phase 7-8).

Keeping both in one module is fine at this project's size (Section 49:
no unnecessary abstraction). If it grows unwieldy we can split into
kb_schemas.py / api_schemas.py later.
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator

# Sentinel used in the knowledge base's dynamic (DYN-###) records in place
# of a real URL, since those records describe "any college" rather than a
# single fixed source. The retrieval/response layer must recognize this and
# never render it as a clickable link (see Phase 2 inspection notes).
UNRESOLVED_SOURCE_SENTINEL = "COLLEGE_OFFICIAL_SOURCE_REQUIRED"


class SourceHierarchyEntry(BaseModel):
    """One entry in a record's source_hierarchy list."""

    rank: int
    source_type: str
    source_name: str


class FAQRecord(BaseModel):
    """
    A single FAQ record from faq_records.

    Field set matches schema_notes.required_fields in the knowledge base,
    plus the optional follow_up_questions field the data actually includes
    (present in every record we inspected, but modeled as optional so a
    future record without it doesn't fail validation).
    """

    id: str
    category: str
    canonical_question: str
    alternative_user_questions: list[str] = Field(default_factory=list)
    answer: str
    source_hierarchy: list[SourceHierarchyEntry] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    information_type: str  # "stable" | "policy_dependent" | "dynamic"
    verification_date: str
    keywords: list[str] = Field(default_factory=list)
    confidence: float
    update_rule: str
    dynamic: bool
    requires_current_verification: bool
    follow_up_questions: list[str] = Field(default_factory=list)

    @field_validator("confidence")
    @classmethod
    def confidence_in_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence must be between 0 and 1, got {v}")
        return v

    @property
    def has_unresolved_sources(self) -> bool:
        """True if any source_url is the placeholder sentinel rather than
        a real, linkable URL."""
        return any(u == UNRESOLVED_SOURCE_SENTINEL for u in self.source_urls)

    @property
    def resolved_source_urls(self) -> list[str]:
        """source_urls with the sentinel filtered out — safe to render as links."""
        return [u for u in self.source_urls if u != UNRESOLVED_SOURCE_SENTINEL]


class RetrievalMethodInfo(BaseModel):
    primary: str
    similarity: str
    retrieval_text_fields: list[str]
    recommended_top_k: int
    initial_similarity_threshold: float
    threshold_note: Optional[str] = None


class ProjectMeta(BaseModel):
    name: str
    version: str
    schema_version: str
    record_count: int
    retrieval_method: RetrievalMethodInfo
    fallback_policy: str
    dynamic_information_policy: str


class KnowledgeBaseDocument(BaseModel):
    """The full shape of CollegePath_AI_Master_Knowledge_Base_v1.json.

    We validate the whole document (not just faq_records) so a corrupted
    `project` or `source_registry` block is caught at startup rather than
    causing a confusing failure later.
    """

    project: ProjectMeta
    source_registry: dict
    categories: list[str]
    faq_records: list[FAQRecord]
    schema_notes: dict


# --- API response contracts (Phase 7) ---


class SourceInfo(BaseModel):
    """Section 21: every substantive answer exposes where it came from.

    `url` is Optional and deliberately None (never the raw sentinel
    string) when the record's top-ranked source has no real, linkable
    URL — e.g. a Dynamic College Information record whose true source is
    "the specific college's official website," which doesn't resolve to
    one fixed link. The frontend should treat a missing url as "point the
    user to the official source directly," not as a broken link.
    """

    name: str
    url: Optional[str] = None


class ChatResponse(BaseModel):
    """
    The /chat endpoint's response contract (Section 25/52).

    `similarity_score` is the retrieval engine's cosine-similarity score
    for the matched record — NOT the knowledge base's `confidence` field,
    and never presented as a probability of correctness (Section 16).
    It's None for fallback responses, since there is no confident match
    to report a score for.
    """

    answer: str
    matched_question: Optional[str] = None
    category: Optional[str] = None
    similarity_score: Optional[float] = None
    source: Optional[SourceInfo] = None
    verification_date: Optional[str] = None
    related_questions: list[str] = Field(default_factory=list)
    fallback: bool
    requires_current_verification: bool


class ChatRequest(BaseModel):
    """
    The /chat endpoint's request body (Section 25).

    Deliberately just `message: str` with no length/emptiness constraint
    here — FastAPI/Pydantic already reject a missing field or a non-string
    type automatically (422), which covers Section 26's "missing fields"
    and "unexpected data types". Emptiness and max-length are business
    rules, not shape rules, so they're enforced once, in
    ChatbotService.validate_query(), rather than duplicated here.
    """

    message: str


class CategoriesResponse(BaseModel):
    """The /categories endpoint's response contract (Section 25)."""

    categories: list[str]
