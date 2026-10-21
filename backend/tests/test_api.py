"""
API tests (Section 38) for GET /health, GET /categories, and POST /chat.

Uses FastAPI's TestClient as a context manager so the app's lifespan
(knowledge base load + TF-IDF fit + service construction) actually runs
against the real knowledge base before each test — these are genuine
integration tests, not mocked-out unit tests of the routing layer alone.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# --- GET /health ---

def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# --- GET /categories ---

def test_categories_returns_all_sixteen(client):
    response = client.get("/categories")
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    assert len(data["categories"]) == 16


def test_categories_includes_expected_names(client):
    response = client.get("/categories")
    categories = response.json()["categories"]
    assert "Gap Years" in categories
    assert "Dynamic College Information" in categories
    assert "Financial Aid" in categories


# --- POST /chat: happy paths ---

def test_chat_confident_answer_has_expected_shape(client):
    response = client.post("/chat", json={"message": "What is Early Action?"})
    assert response.status_code == 200
    data = response.json()
    assert data["fallback"] is False
    assert data["category"] == "Decision Types"
    assert data["matched_question"] == "What is Early Action?"
    assert isinstance(data["similarity_score"], float)
    assert data["source"]["name"]
    assert data["source"]["url"].startswith("https://")
    assert data["requires_current_verification"] is False
    assert len(data["related_questions"]) > 0


def test_chat_fallback_answer_has_expected_shape(client):
    response = client.post("/chat", json={"message": "What is the capital of France?"})
    assert response.status_code == 200
    data = response.json()
    assert data["fallback"] is True
    assert data["matched_question"] is None
    assert data["category"] is None
    assert data["similarity_score"] is None
    assert data["source"] is None
    assert len(data["related_questions"]) > 0


def test_chat_dynamic_record_flags_verification_and_hides_placeholder_url(client):
    response = client.post(
        "/chat", json={"message": "What is the current application deadline for MIT?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["fallback"] is False
    assert data["requires_current_verification"] is True
    assert data["category"] == "Dynamic College Information"
    # The sentinel must never leak into the API response as a fake link.
    assert data["source"]["url"] is None
    assert "COLLEGE_OFFICIAL_SOURCE_REQUIRED" not in response.text


def test_chat_never_invents_a_specific_deadline(client):
    # Section 24: the answer must not state a specific date.
    response = client.post(
        "/chat", json={"message": "What is the current application deadline for Stanford?"}
    )
    data = response.json()
    assert "2026" not in data["answer"] and "2027" not in data["answer"]


# --- POST /chat: validation errors (Section 26/37) ---

def test_chat_empty_message_returns_400(client):
    response = client.post("/chat", json={"message": ""})
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_chat_whitespace_only_message_returns_400(client):
    response = client.post("/chat", json={"message": "     "})
    assert response.status_code == 400


def test_chat_too_long_message_returns_400(client):
    response = client.post("/chat", json={"message": "a" * 501})
    assert response.status_code == 400
    assert "maximum length" in response.json()["detail"].lower()


def test_chat_missing_message_field_returns_422(client):
    response = client.post("/chat", json={})
    assert response.status_code == 422


def test_chat_wrong_type_message_returns_422(client):
    response = client.post("/chat", json={"message": 12345})
    assert response.status_code == 422


def test_chat_malformed_json_returns_422(client):
    response = client.post(
        "/chat",
        content="{not valid json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_chat_error_responses_never_include_a_stack_trace(client):
    response = client.post("/chat", json={"message": ""})
    body = response.text
    assert "Traceback" not in body
    assert ".py" not in body


# --- Defense in depth: unexpected server errors never leak internals ---

def test_unhandled_exception_returns_clean_500(monkeypatch):
    # TestClient re-raises unhandled exceptions by default (for local
    # debugging convenience) even when a global handler is registered —
    # raise_server_exceptions=False switches it to the same behavior a
    # real deployed server would show an actual client: the handler's
    # JSON response, not a re-raised Python exception.
    with TestClient(app, raise_server_exceptions=False) as client:
        def boom(*args, **kwargs):
            raise RuntimeError("this internal detail must never reach the client")

        monkeypatch.setattr(app.state.chatbot_service, "answer_query", boom)

        response = client.post("/chat", json={"message": "What is Early Action?"})
        assert response.status_code == 500
        assert "this internal detail" not in response.text
        assert "Traceback" not in response.text
        assert response.json()["detail"] == "An internal server error occurred."


# --- Swagger / OpenAPI availability (Section 25: documented via Swagger UI) ---

def test_docs_endpoint_is_available(client):
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_schema_is_available_and_lists_all_routes(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/health" in paths
    assert "/categories" in paths
    assert "/chat" in paths


# --- Phase 11 manual-QA findings, locked in as regression tests ---

def test_chat_handles_unicode_and_emoji(client):
    response = client.post(
        "/chat", json={"message": "¿Qué es un gap year? 😊"}
    )
    assert response.status_code == 200
    assert response.json()["category"] == "Gap Years"


def test_chat_never_echoes_raw_user_input_back(client):
    # The response only ever contains vetted KB content (the matched
    # record's own answer/canonical_question), never the user's literal
    # message — so there is no server-side reflection surface for
    # injected content to begin with, regardless of what the frontend
    # does with it.
    injected = "What is <script>alert(1)</script> Early Action?"
    response = client.post("/chat", json={"message": injected})
    assert response.status_code == 200
    assert "<script>" not in response.text


def test_chat_rejects_fullwidth_unicode_whitespace_as_empty(client):
    # U+3000 (ideographic space) is whitespace under Python's str.strip()
    # but easy to miss when eyeballing a "non-empty-looking" string.
    response = client.post("/chat", json={"message": "   \u3000\u3000  "})
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


# --- CORS (Phase 10 integration finding) ---
#
# Browsers treat http://localhost:5173 and http://127.0.0.1:5173 as two
# different origins even though they reach the same dev server. Both
# must be allow-listed, or a developer who opens the frontend via
# whichever one isn't gets every fetch() silently blocked by the
# browser's CORS check — the backend itself works fine, curl doesn't
# enforce CORS, so this kind of bug is invisible to curl-only testing
# and only shows up as a real browser's console error.

@pytest.mark.parametrize(
    "origin", ["http://localhost:5173", "http://127.0.0.1:5173"]
)
def test_cors_allows_both_vite_dev_origins(client, origin):
    response = client.get("/health", headers={"Origin": origin})
    assert response.headers.get("access-control-allow-origin") == origin


def test_cors_rejects_unknown_origin(client):
    response = client.get(
        "/health", headers={"Origin": "http://evil.example.com"}
    )
    assert "access-control-allow-origin" not in {
        k.lower() for k in response.headers.keys()
    }


def test_cors_preflight_allows_post_chat_with_json_content_type(client):
    # This is the exact preflight a browser sends before every POST
    # /chat call, since "application/json" is not a CORS-simple content
    # type. If this fails, no chat message would ever reach the backend
    # from a real browser, even though a plain POST via curl works fine.
    response = client.options(
        "/chat",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert "POST" in response.headers.get("access-control-allow-methods", "")
    assert (
        response.headers.get("access-control-allow-origin")
        == "http://localhost:5173"
    )
