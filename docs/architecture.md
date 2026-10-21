# Architecture

## Overview

CollegePath AI is a three-layer system: a React frontend, a FastAPI
backend, and a static JSON knowledge base. There is no database and no
external AI/LLM API call in the retrieval path — the "intelligence" is
entirely TF-IDF + cosine similarity over a curated FAQ set, by design
(this is the CodeAlpha internship's core technical requirement).

```
User
  │
  ▼
React Frontend (Vite dev server, :5173)
  │  fetch("/api/...") — proxied to the backend, /api prefix stripped
  ▼
FastAPI Backend (:8000)
  │
  ├─ GET  /health       → liveness check
  ├─ GET  /categories   → reads KnowledgeBaseService.categories (in memory)
  └─ POST /chat         → ChatbotService.answer_query(message)
                              │
                              ▼
                     ChatbotService (app/services/chatbot.py)
                              │
                validate_query()         — Section 26/37 input validation
                              │
                RetrievalEngine.retrieve() — Section 15 pipeline:
                    preprocess → TF-IDF transform → cosine_similarity
                    → sort → top-k
                              │
                apply_threshold()        — Section 17/18 confidence gate
                              │
                build_source_info()      — Section 21/22 source attribution
                              │
                              ▼
                         ChatResponse
```

## Startup sequence

Everything is built once, at FastAPI startup (`app/main.py`), and held
on `app.state` for the life of the process — nothing here is rebuilt
per-request:

1. `KnowledgeBaseService.load()` — reads and validates the JSON
   (147 records, 16 categories). A validation failure is fatal: the
   app refuses to start rather than serve with a broken knowledge base.
2. `TfidfIndex.fit()` — builds the retrieval corpus (canonical question
   + alternatives + keywords, per record) and fits one shared
   `TfidfVectorizer` against it (1,056 vocabulary terms in the current
   corpus).
3. `RetrievalEngine(tfidf_index)` — wraps the fitted index with cosine
   similarity + top-k ranking.
4. `ChatbotService(retrieval_engine)` — the orchestration layer every
   route actually talks to.

## Directory layout

```
backend/app/
  main.py              FastAPI app, startup wiring, CORS, global error handler
  core/
    config.py          All tunables (threshold, top_k, CORS origins, paths)
    exceptions.py       KnowledgeBaseLoadError, InvalidQueryError, RetrievalError
    logging.py          Startup/error logging (never logs full user queries)
  models/schemas.py     Pydantic models — both the KB's own schema AND the API contract
  services/
    knowledge_base.py   Load, validate, index the FAQ JSON
    preprocessing.py     Text normalization + retrieval-corpus construction
    retrieval.py          TfidfIndex (Phase 4) + RetrievalEngine (Phase 5)
    chatbot.py             Threshold/fallback/related-questions + full orchestration
  api/routes/
    health.py, categories.py, chat.py    Thin route handlers only

frontend/src/
  services/api.js       All HTTP calls to the backend, nowhere else
  hooks/useChat.js       Owns messages/loading/category state
  components/            One component per concern (chat, input, source card, etc.)
```

## Why no database, no vector DB, no LLM call

The knowledge base is 147 records — small enough to fit entirely in
memory, and Section 64 explicitly asks that this project not
overengineer with infrastructure a dataset this size doesn't need.
TF-IDF + cosine similarity is the assigned retrieval method (Section 2);
an LLM call would work but would defeat the point of demonstrating the
underlying NLP/IR technique this internship is meant to show.

## Known architectural limitations (documented, not hidden)

- **Pure lexical retrieval.** TF-IDF has no concept of synonymy — "year
  off" and "gap year" don't automatically match. See `docs/retrieval.md`
  for the measured impact of this.
- **No conversational state.** Each `/chat` call is independent; the
  backend has no memory of prior turns in a session. The knowledge
  base's `follow_up_questions` field was originally written for a
  stateful, slot-filling dialogue manager (confirmed by inspecting all
  306 entries — see `docs/retrieval.md`); building that manager was
  judged out of scope, so that field is intentionally unused in the
  final design.
- **Single-process, in-memory state.** Fine for this dataset size;
  would need externalizing (e.g. a shared cache) before running
  multiple backend replicas behind a load balancer.
