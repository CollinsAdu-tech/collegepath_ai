# CollegePath AI

> Navigate college admissions with clarity.

An AI-powered college-admissions FAQ chatbot built for a CodeAlpha AI
Internship. Retrieval is implemented with **TF-IDF + cosine similarity**
over a curated 147-record FAQ knowledge base — no embeddings, no LLM API
call in the retrieval path, per the internship's core technical
requirement.

## Features

- **TF-IDF + cosine similarity retrieval** over the full knowledge base,
  fit once at startup (never refit per query)
- **Confidence threshold + fallback** — never guesses when retrieval is
  weak; the threshold (0.40) was set from a measured evaluation, not a
  guess (see `docs/retrieval.md`)
- **Source attribution** on every confident answer, with real links —
  and honest "check the official page directly" text (never a fake
  link) for the 12 records whose true source varies by college
- **Dynamic-information detection** — deadline/policy/rate questions
  about specific colleges are flagged as needing current verification
  and never state an invented date or number
- **Guided related-questions** that are guaranteed to resolve
  confidently if clicked (a real bug where this wasn't true was found
  and fixed — see `docs/retrieval.md`)
- **Formal retrieval evaluation** — a documented 40-query set measuring
  top-1/top-3 accuracy and the dangerous "wrong-confident" failure mode
  separately from safe fallbacks
- Category chips, suggested questions, loading/error states, and
  frontend-only feedback buttons
- Responsive, accessible UI (semantic HTML, visible focus states,
  skip link, error boundary)

## Architecture

```
React (Vite, :5173) --/api proxy--> FastAPI (:8000) --> ChatbotService
                                                            │
                                          preprocess -> TF-IDF -> cosine
                                          similarity -> threshold ->
                                          source attribution -> response
```

Full diagram and startup sequence: [`docs/architecture.md`](docs/architecture.md).

## Tech stack

```
Python · FastAPI · scikit-learn (TfidfVectorizer, cosine_similarity) · Pydantic
React · Vite
```

## Installation

**Backend**
```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Frontend**
```bash
cd frontend
npm install
```

## Running locally

```bash
# Terminal 1
cd backend
uvicorn app.main:app --reload
# http://localhost:8000/health, http://localhost:8000/docs (Swagger UI)

# Terminal 2
cd frontend
npm run dev
# http://localhost:5173
```

## API endpoints

`GET /health` · `GET /categories` · `POST /chat`

Full request/response shapes, status codes, and examples:
[`docs/api.md`](docs/api.md).

## Testing

```bash
cd backend
pytest -v                          # 137 tests
pytest tests/test_evaluation.py -s  # full retrieval evaluation report
```

Testing philosophy, what's covered, and what's intentionally manual:
[`docs/testing.md`](docs/testing.md) ·
[`docs/manual-qa-checklist.md`](docs/manual-qa-checklist.md).

## Retrieval methodology

TF-IDF (unigrams + bigrams) fit once over `canonical_question +
alternative_user_questions + keywords` per record; cosine similarity
ranks all 147 records against a normalized query; a 0.40 similarity
threshold (set from measured data, not the spec's 0.30 starting point —
see below) gates whether to answer or fall back.

Full methodology, the threshold-tuning investigation, and the formal
evaluation results: [`docs/retrieval.md`](docs/retrieval.md).

## Limitations

- **Static knowledge base.** Nothing is fetched live; "current"
  information (deadlines, acceptance rates, policies) is explicitly
  flagged as needing verification rather than answered directly.
- **Pure lexical retrieval.** No synonym understanding — two genuine
  "wrong-confident" cases in the 40-query evaluation are caused by
  word-overlap with an adjacent category's vocabulary, not a code bug.
  Documented in detail in `docs/retrieval.md`.
- **No guaranteed outcomes.** The system never states or implies a
  guarantee of admission, scholarship, or financial aid.
- **No conversational memory.** Each `/chat` call is independent; there
  is no multi-turn dialogue state.
- **28% of on-domain test queries safely decline rather than answer**
  (vs. 8% that answer confidently but wrong) — a deliberate asymmetry:
  Section 18 treats an unhelpful-but-safe fallback as far preferable to
  a confidently wrong answer.

## Deployment

Not deployed as part of this build — see
[`docs/deployment.md`](docs/deployment.md) for the recommended
platforms (Render + Vercel), the exact steps, and the production
environment variables (`CORS_ORIGINS` on the backend,
`VITE_API_BASE_URL` on the frontend) needed for a split-origin
deployment.

## Future improvements

- Embedding-based or hybrid retrieval to close the two documented
  lexical-overlap gaps
- A real live-verification service for Dynamic College Information
  records (Section 46's intended future architecture)
- A stateful dialogue layer that could actually use the knowledge
  base's `follow_up_questions` field for its original intended purpose
  (currently unused — see `docs/retrieval.md` for why)
- Backend-persisted feedback (currently frontend-only, by design —
  Section 33)
- A larger, deduplicated knowledge base (Phase 1/6 found real
  duplicate-content issues in several records' alternative questions)
