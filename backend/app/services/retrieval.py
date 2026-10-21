"""
Retrieval engine.

Two layers, built incrementally across Phases 4-5:

1. TfidfIndex (Phase 4) — fits ONE shared TfidfVectorizer against the FAQ
   knowledge-base corpus at startup and transforms user queries into that
   same vector space. Knows nothing about similarity or ranking.

2. RetrievalEngine (Phase 5, this addition) — wraps a fitted TfidfIndex,
   computes cosine similarity between a query vector and every record
   vector, and returns the top-k matches ranked by similarity score.

Deliberately NOT in this file yet: threshold decisions (is the top match
"good enough" to answer with?) and fallback responses. Those belong to
the ChatbotService in Phase 6/7, which will call RetrievalEngine.retrieve()
and decide what to do with the results — this engine's job stops at
"here are the best-matching records and their scores."
"""

from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.exceptions import RetrievalError
from app.core.logging import logger
from app.models.schemas import FAQRecord
from app.services.preprocessing import build_corpus, preprocess_query


class TfidfIndex:
    """Fits and holds the shared TF-IDF vector space for the FAQ corpus."""

    def __init__(self, records: list[FAQRecord]):
        if not records:
            raise ValueError("TfidfIndex requires at least one FAQ record.")
        self._records = records
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None  # scipy sparse matrix, shape (n_records, n_terms)
        self._fitted = False

    def fit(self) -> None:
        """
        Build the retrieval corpus and fit the vectorizer against it.

        Must be called exactly once, at startup, against the full record
        set — never per-query (Section 44: "Do NOT refit TF-IDF for every
        user query").
        """
        corpus = build_corpus(self._records)

        self._vectorizer = TfidfVectorizer(
            # Redundant given preprocessing already lowercases everything,
            # but explicit here so this vectorizer's own config never
            # silently relies on case-sensitive matching if preprocessing
            # ever changes.
            lowercase=True,
            # Unigrams AND bigrams. Admissions terminology is often a
            # two-word phrase — "gap year", "early action", "financial
            # aid", "test optional" — and treating those as a single
            # bigram feature carries more distinguishing signal than the
            # two unigrams alone (e.g. "early" and "action" separately
            # are common; "early action" together is specific).
            ngram_range=(1, 2),
        )
        self._matrix = self._vectorizer.fit_transform(corpus)
        self._fitted = True

        logger.info(
            f"TF-IDF vectorizer fit: {self._matrix.shape[0]} records, "
            f"{self._matrix.shape[1]} vocabulary terms (unigrams + bigrams)."
        )

    def transform_query(self, query: str):
        """
        Preprocess and transform a raw user query into the same vector
        space as the fitted corpus. Returns a 1-row sparse matrix.

        A query with no vocabulary overlap at all (e.g. "asdkjfh") still
        transforms cleanly to an all-zero vector — sklearn does not raise
        for out-of-vocabulary terms, it simply ignores them. That all-zero
        vector is exactly what should drive a low/zero similarity score
        and trigger the fallback in Phase 5/6.
        """
        self._ensure_fitted()
        normalized = preprocess_query(query)
        return self._vectorizer.transform([normalized])

    @property
    def matrix(self):
        self._ensure_fitted()
        return self._matrix

    @property
    def vectorizer(self) -> TfidfVectorizer:
        self._ensure_fitted()
        return self._vectorizer

    @property
    def records(self) -> list[FAQRecord]:
        return self._records

    @property
    def vocabulary_size(self) -> int:
        self._ensure_fitted()
        return len(self._vectorizer.vocabulary_)

    @property
    def is_fitted(self) -> bool:
        return self._fitted

    def _ensure_fitted(self) -> None:
        if not self._fitted:
            raise RetrievalError(
                "TfidfIndex.fit() must be called before it can be used."
            )


@dataclass(frozen=True)
class RetrievalMatch:
    """One ranked result: a candidate FAQ record and its cosine-similarity
    score against a specific query. `similarity` is a retrieval score in
    [0, 1] — NOT the same thing as the record's own `confidence` field
    (Section 16). The two must never be conflated when formatting a
    response in later phases."""

    record: FAQRecord
    similarity: float


class RetrievalEngine:
    """
    Ranks FAQ records against a user query using cosine similarity over
    the shared TF-IDF vector space built by TfidfIndex.
    """

    def __init__(self, tfidf_index: TfidfIndex, default_top_k: int = 3):
        if not tfidf_index.is_fitted:
            raise RetrievalError(
                "RetrievalEngine requires a TfidfIndex that has already "
                "been fit()."
            )
        if default_top_k < 1:
            raise ValueError("default_top_k must be at least 1.")
        self._index = tfidf_index
        self._default_top_k = default_top_k

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievalMatch]:
        """
        Rank every FAQ record against `query` by cosine similarity and
        return the top-k matches, highest similarity first.

        Process (Section 15):
            query -> preprocess -> TF-IDF transform
                  -> cosine_similarity against every record vector
                  -> sort descending -> take top-k

        top_k is clamped to the number of available records, so asking
        for more matches than exist in the knowledge base doesn't raise.
        """
        k = top_k if top_k is not None else self._default_top_k
        if k < 1:
            raise ValueError("top_k must be at least 1.")
        k = min(k, len(self._index.records))

        query_vector = self._index.transform_query(query)

        # cosine_similarity(query_vector, matrix) -> shape (1, n_records);
        # [0] flattens it to a 1D array of per-record scores.
        similarities = cosine_similarity(query_vector, self._index.matrix)[0]

        # argsort() sorts ascending; reverse it, then take the first k
        # indices to get the k highest-similarity records, best first.
        ranked_indices = similarities.argsort()[::-1][:k]

        return [
            RetrievalMatch(
                record=self._index.records[i],
                similarity=float(similarities[i]),
            )
            for i in ranked_indices
        ]
