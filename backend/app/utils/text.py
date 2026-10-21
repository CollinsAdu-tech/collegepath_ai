"""
Low-level text normalization utilities.

This is the single place text cleanup happens, so every consumer
(user queries, canonical questions, alternative questions, keywords)
goes through exactly the same transformation (Section 12). If we ever
need to change how text is normalized, this is the only file to touch.
"""

import re

# Matches any character that is NOT a "word" character (\w = letters,
# digits, underscore, and — importantly — Unicode letters, so accented
# names in college questions aren't mangled) and not whitespace.
_NON_WORD_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """
    Normalize a piece of text for TF-IDF matching.

    Steps (Section 12):
      1. Lowercase.
      2. Strip punctuation (question marks, commas, apostrophes, etc.)
         by replacing it with a space — NOT deleting it outright, so
         "don't" doesn't become "dont" glued together in a way that
         changes token boundaries unpredictably, and "well-funded"
         doesn't become "wellfunded".
      3. Collapse repeated whitespace (spaces, tabs, newlines) to a
         single space.
      4. Strip leading/trailing whitespace.

    Deliberately does NOT remove stopwords or stem/lemmatize — words
    like "international", "students", "financial", "aid" must survive
    intact, and aggressive normalization risks losing exactly the terms
    that distinguish one admissions FAQ from another (Section 12).

    An empty or whitespace-only input returns "" rather than raising —
    query-level validation (empty message rejected) is a separate
    concern handled by the chatbot/API layer, not this utility.
    """
    if not isinstance(text, str):
        raise TypeError(f"normalize_text expects a string, got {type(text)}")

    normalized = text.lower()
    normalized = _NON_WORD_RE.sub(" ", normalized)
    normalized = _WHITESPACE_RE.sub(" ", normalized).strip()
    return normalized
