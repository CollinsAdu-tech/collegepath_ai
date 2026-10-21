"""
Knowledge base loading service.

Responsibilities (Section 11):
- Load the JSON once.
- Validate it against the expected schema (via Pydantic models).
- Fail loudly and clearly if the file is missing or malformed.
- Keep the validated records in memory, indexed for fast lookup.
- Expose the record list to the retrieval engine (Phase 4) without that
  engine needing to know anything about file I/O or JSON structure.

This service does NOT do any TF-IDF work — that's RetrievalEngine's job
(Phase 4). Keeping the two separate means the knowledge base can be
swapped, re-validated, or hot-reloaded independently of the retrieval
implementation.
"""

import json
from pathlib import Path

from pydantic import ValidationError

from app.core.exceptions import KnowledgeBaseLoadError
from app.core.logging import logger
from app.models.schemas import FAQRecord, KnowledgeBaseDocument


class KnowledgeBaseService:
    """Loads and holds the validated FAQ knowledge base in memory."""

    def __init__(self, path: Path):
        self._path = path
        self._records: list[FAQRecord] = []
        self._by_id: dict[str, FAQRecord] = {}
        self._by_category: dict[str, list[FAQRecord]] = {}
        self._categories: list[str] = []
        self._loaded = False

    def load(self) -> None:
        """Read, parse, and validate the knowledge base file.

        Raises KnowledgeBaseLoadError on any failure. This is intentionally
        fatal: the app should not start up and silently serve zero FAQs.
        """
        if not self._path.exists():
            raise KnowledgeBaseLoadError(
                f"Knowledge base file not found at: {self._path}"
            )

        try:
            raw_text = self._path.read_text(encoding="utf-8")
        except OSError as exc:
            raise KnowledgeBaseLoadError(
                f"Could not read knowledge base file at {self._path}: {exc}"
            ) from exc

        try:
            raw_data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise KnowledgeBaseLoadError(
                f"Knowledge base file is not valid JSON: {exc}"
            ) from exc

        try:
            document = KnowledgeBaseDocument.model_validate(raw_data)
        except ValidationError as exc:
            # Pydantic's error message already lists exactly which
            # field(s), on which record(s), failed validation.
            raise KnowledgeBaseLoadError(
                f"Knowledge base failed schema validation:\n{exc}"
            ) from exc

        if len(document.faq_records) == 0:
            raise KnowledgeBaseLoadError(
                "Knowledge base loaded but contains zero faq_records."
            )

        # Detect duplicate IDs — a corrupted/edited KB could introduce these,
        # and duplicate IDs would make get_by_id() and source attribution
        # ambiguous.
        seen_ids: set[str] = set()
        for record in document.faq_records:
            if record.id in seen_ids:
                raise KnowledgeBaseLoadError(
                    f"Duplicate FAQ record id found: {record.id}"
                )
            seen_ids.add(record.id)

        self._records = document.faq_records
        self._by_id = {r.id: r for r in self._records}
        self._categories = document.categories

        by_category: dict[str, list[FAQRecord]] = {c: [] for c in self._categories}
        for record in self._records:
            if record.category not in by_category:
                # A record references a category that wasn't declared in
                # the top-level `categories` list. Not necessarily fatal,
                # but worth surfacing loudly rather than silently dropping it.
                logger.warning(
                    f"Record {record.id} has undeclared category "
                    f"'{record.category}'; adding it to the category index."
                )
                by_category[record.category] = []
            by_category[record.category].append(record)
        self._by_category = by_category

        self._loaded = True
        logger.info(
            f"Knowledge base loaded: {len(self._records)} records across "
            f"{len(self._categories)} categories from {self._path.name}."
        )

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def records(self) -> list[FAQRecord]:
        self._ensure_loaded()
        return self._records

    @property
    def categories(self) -> list[str]:
        self._ensure_loaded()
        return self._categories

    def get_by_id(self, record_id: str) -> FAQRecord | None:
        self._ensure_loaded()
        return self._by_id.get(record_id)

    def get_by_category(self, category: str) -> list[FAQRecord]:
        self._ensure_loaded()
        return self._by_category.get(category, [])

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            raise KnowledgeBaseLoadError(
                "Knowledge base accessed before load() was called."
            )
