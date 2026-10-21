# Testing

## Running the tests

```bash
cd backend
pip install -r requirements.txt
pytest -v
```

For the full formal evaluation report (per-query breakdown, not just
pass/fail):
```bash
pytest tests/test_evaluation.py -s
```

## Current state: 137 tests, all passing

| File | Tests | Covers |
|---|---|---|
| `test_knowledge_base.py` | 16 | JSON loading, schema validation, category/id indexing, failure paths (missing file, invalid JSON, missing field, duplicate ids, empty records) |
| `test_preprocessing.py` | 16 | Text normalization, retrieval-corpus construction, deduplication |
| `test_retrieval.py` | 30 | TF-IDF fitting/vocabulary, cosine similarity, ranking, top-k, threshold-adjacent sanity checks |
| `test_chatbot.py` | 42* | Threshold decisions, related-question selection, full `ChatbotService` orchestration, dynamic-record handling |
| `test_api.py` | 23* | All three HTTP routes, validation status codes (400/422/500), CORS, Unicode/injection edge cases |
| `test_evaluation.py` | 7 | The formal 40-query retrieval evaluation (see `docs/retrieval.md`) |

*Includes parametrized cases (e.g. one test function run across several
CORS origins or several seed queries counts as several collected tests).

## Testing philosophy used throughout this project

**Every layer is tested against the real knowledge base, not just
synthetic fixtures.** Synthetic `FAQRecord` objects are used for testing
specific mechanisms in isolation (e.g. "does ranking sort descending"),
but every service also has tests that load the actual 147-record JSON
and check real behavior — this is what caught the `FAQ-037` duplication
bug, the CORS origin mismatch, and the `follow_up_questions` dead-end,
none of which would have surfaced from synthetic-only tests.

**Full-stack integration was tested with real running servers, not just
mocked HTTP.** Several bugs (CORS, the dead-end related-questions issue)
were only visible when the actual FastAPI backend and actual Vite dev
server were run together and exercised with realistic `Origin` headers
and multi-turn conversation sequences — `TestClient`-only testing would
have missed both.

**Dangerous failures are measured separately from merely unhelpful
ones.** The evaluation suite tracks "confidently wrong" (bad) separately
from "safely declined" (merely unhelpful) — collapsing them into one
"accuracy" number would have hidden which failure mode actually matters
per Section 18.

**Test assertions reflect measured behavior, not aspirational
targets.** Every accuracy/rate threshold asserted in
`test_evaluation.py` is set at or slightly below a number that was
actually observed and printed, per Section 39/40's explicit instruction
not to claim an accuracy score without measuring it.

## What is intentionally NOT automated

Keyboard navigation, focus rings, responsive layout at various
viewport widths, and duplicate-submit prevention under real click
timing all require a human in an actual browser — see
`docs/manual-qa-checklist.md`.

## Known, documented (not hidden) retrieval limitations

Two genuine wrong-confident cases remain in the 40-query evaluation set,
caused by pure lexical (no-synonymy) TF-IDF matching against adjacent
categories' vocabulary. See `docs/retrieval.md` for the specific
examples and why fixing them is out of scope (would require
embedding-based retrieval, which Section 2 excludes).
