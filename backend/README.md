# CollegePath AI — Backend

FastAPI backend implementing TF-IDF + cosine-similarity retrieval over a
college-admissions FAQ knowledge base (147 records, 16 categories).

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

Visit http://localhost:8000/health and http://localhost:8000/docs (Swagger UI).

## Test

```bash
pytest -v                           # 137 tests
pytest tests/test_evaluation.py -s  # full retrieval evaluation report
```

## Configuration

Copy `.env.example` to `.env` to override defaults (similarity
threshold, top-k, max query length, CORS origins). See
`app/core/config.py` for what each value does and why its default was
chosen.

See `../docs/` for architecture, retrieval methodology, API reference,
and testing philosophy.
