# Retrieval Methodology

## The pipeline

```
User query
   │
   ▼
normalize_text()          lowercase, strip punctuation to spaces, collapse whitespace
   │                      (deliberately NO stopword removal or stemming — Section 12:
   │                       words like "international"/"financial"/"aid" must survive intact)
   ▼
TfidfVectorizer.transform()   using the SAME vectorizer fit at startup — never refit per query
   │                          (lowercase=True, ngram_range=(1,2): unigrams AND bigrams,
   │                           since "gap year"/"early action"/"financial aid" carry more
   │                           signal as a phrase than as two separate words)
   ▼
cosine_similarity(query_vector, corpus_matrix)   → one score per FAQ record, in [0, 1]
   │
   ▼
sort descending → top_k (3)
   │
   ▼
apply_threshold()   top score >= 0.40 ? answer with it : fall back
```

## TF-IDF corpus construction

Each FAQ record contributes one string to the corpus:
`canonical_question + alternative_user_questions + keywords`, each part
normalized individually before joining, **with duplicate normalized
parts removed**. The answer text is deliberately excluded — retrieval
matches the user's *question*, not the *answer's* content.

The deduplication step was added after a real bug was found during
threshold tuning (see below) — it wasn't part of the original design.

## Retrieval similarity vs. knowledge-base confidence

These are two unrelated numbers and the codebase keeps them physically
separate (`RetrievalMatch.similarity` vs `FAQRecord.confidence`):

- **`confidence`** (in the KB JSON) is the knowledge base author's own
  data-quality rating for that record. It says nothing about whether a
  *given query* was matched well.
- **`similarity_score`** (computed per-query) is how close the user's
  question was to this record, geometrically, in TF-IDF space. It is
  never shown to the user as a "confidence %" (Section 16) — the UI only
  ever shows a status dot and category pill, never the raw number.

## The threshold: why 0.40, not the suggested 0.30

Section 17 suggests 0.30 as a starting point. An early check with
Section 62's example off-domain queries showed **"What is the capital of
France?" scoring 0.36** — above 0.30 — which traced back to a real data
artifact: `FAQ-037`'s alternative questions repeated its canonical
question ("What is the SAT?") near-verbatim, inflating the weight of
generic words like "what"/"is"/"the" for that one record. Fixing the
corpus-construction deduplication reduced but didn't eliminate the
problem (the vocabulary shrank from 1,099 to 1,056 terms).

An 18-query threshold sweep (10 on-domain, 8 off-domain) found:

| threshold | on-domain false-negatives | off-domain false-positives |
|---|---|---|
| 0.30 | 1/10 | 3/8 |
| 0.35 | 1/10 | 1/8 |
| **0.40** | **2/10** | **0/8** |
| 0.45 | 3/10 | 0/8 |

0.40 was the first value with zero off-domain false positives, at the
cost of one more on-domain question falling back. Per Section 18, a
safe "please rephrase" is a better failure mode than a confidently
wrong answer, so 0.40 became the production default
(`SIMILARITY_THRESHOLD` in `.env` / `config.py`).

## Formal evaluation (Section 39)

A 40-query set (`tests/fixtures/evaluation_queries.py`) covering all 16
categories, 8 harder paraphrases, 12 off-domain queries, and 4
short/edge-case queries was scored against the production threshold
(`tests/test_evaluation.py`, run with `pytest tests/test_evaluation.py -s`
for the full per-query report). Results, tracking two *different*
failure modes separately because they are not equally bad:

| Metric | Result |
|---|---|
| Correct (confident + right category) | 17/26 = 65% |
| **Wrong-confident** (confident + WRONG category — the dangerous case) | 2/26 = 8% |
| Declined (safe fallback, missed an answer) | 7/26 = 27% |
| Top-3 hit rate | 22/26 = 85% |
| Off-domain correctly declined | 14/14 = 100% |

### The two remaining wrong-confident cases (genuine, documented limitations)

1. *"How do I decide which colleges to apply to?"* matches "How do I
   apply to a U.S. college?" (Application Process, 0.567) instead of
   College Selection's "How should I choose colleges?" — the query
   shares "apply"/"colleges" with the wrong record far more than
   "choose"/"compare" with the right one.
2. *"Where can I check if a college's cost of attendance changed?"*
   matches the definitional "What is cost of attendance?" (Financial
   Aid, 0.645) ahead of the Dynamic College Information record for a
   college's *current* cost of attendance (0.543) — the literal phrase
   "cost of attendance" overlaps more with the definition than
   "changed"/"current" overlaps with the dynamic record's wording.

Both are inherent to pure lexical matching — TF-IDF has no notion that
two phrases mean the same thing if they don't share words. Fixing this
class of error would require semantic/embedding-based retrieval, which
Section 2 explicitly puts out of scope for this project.

**Two evaluation-set labeling mistakes were caught and corrected during
this process, not hidden**: I had originally expected "What is the CSS
Profile used for?" to fall under Financial Aid, but the real knowledge
base genuinely files that content under International Students — the
retrieval was right and my expected label was wrong, so I fixed the
label. Likewise a bare "deadlines" query was originally marked
must-fall-back, but it reasonably and correctly matches deadline-
tracking content — that expectation was also corrected.

## The `follow_up_questions` field is intentionally unused for navigation

Every FAQ record includes a `follow_up_questions` field. Initial design
(Phase 6) used it as the primary source for the UI's "related questions"
— clicking one re-submits it as a new query. Phase 10 integration
testing found this produced a **fallback dead end**. Inspecting all 306
entries across the 147 records showed why: 100% of them are one of two
boilerplate templates (a generic pair for regular FAQs; a 3-question
slot-filling set — "What is your intended entry year?", "Are you
applying as an international student?", "Would you like the official
source?" — for the Dynamic College Information records). These are
prompts for a stateful, multi-turn dialogue manager, not standalone
questions this retrieval system can answer on their own.

**Fix:** related questions are now sourced only from the next-best
retrieval matches' `canonical_question` — guaranteed to retrieve
confidently if clicked, since they're literal entries already in the
corpus. A regression test (`test_real_related_questions_never_lead_to_a_dead_end`)
walks several seed queries and asserts every related question they
offer resolves confidently, not just spot-checks one case.
