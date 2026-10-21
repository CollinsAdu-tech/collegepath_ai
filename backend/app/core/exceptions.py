"""
Custom exceptions for CollegePath AI.

Kept intentionally small (Section 51): only exceptions that need to be
caught and handled differently from a generic error get their own class.
"""


class KnowledgeBaseLoadError(Exception):
    """Raised when the knowledge base file is missing, malformed, or fails
    schema validation. This should be fatal at startup — the app cannot
    serve correct answers without a valid knowledge base."""


class InvalidQueryError(Exception):
    """Raised when a user query fails validation (empty, too long, wrong type)."""


class RetrievalError(Exception):
    """Raised when the retrieval engine is used incorrectly, e.g. before
    the TF-IDF vectorizer has been fit against the knowledge base."""
