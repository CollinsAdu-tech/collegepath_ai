"""
CollegePath AI — FastAPI application entrypoint.

Startup wires the full backend pipeline: load knowledge base -> fit
TF-IDF -> build RetrievalEngine -> build ChatbotService. Routes:
GET /health, GET /categories, POST /chat — all thin wrappers around
services built at startup and stored on app.state.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import categories, chat, health
from app.core.config import settings
from app.core.exceptions import KnowledgeBaseLoadError
from app.core.logging import logger
from app.services.chatbot import ChatbotService
from app.services.knowledge_base import KnowledgeBaseService
from app.services.retrieval import RetrievalEngine, TfidfIndex


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: load knowledge base -> fit TF-IDF -> build RetrievalEngine
    -> build ChatbotService, each stored on app.state so route handlers
    can reach them without re-doing any of this work per-request
    (Section 44). A knowledge-base load failure is fatal — raising here
    stops the app from ever accepting traffic with a broken or empty
    knowledge base.

    Nothing is needed on shutdown; everything here is in-memory state
    with no external connections to close.
    """
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} starting up.")

    kb_service = KnowledgeBaseService(settings.KNOWLEDGE_BASE_PATH)
    try:
        kb_service.load()
    except KnowledgeBaseLoadError as exc:
        logger.error(f"Fatal: knowledge base failed to load: {exc}")
        raise

    app.state.knowledge_base = kb_service

    tfidf_index = TfidfIndex(kb_service.records)
    tfidf_index.fit()
    app.state.tfidf_index = tfidf_index

    app.state.retrieval_engine = RetrievalEngine(
        tfidf_index, default_top_k=settings.TOP_K
    )

    app.state.chatbot_service = ChatbotService(app.state.retrieval_engine)

    yield  # app runs here

    logger.info(f"{settings.APP_NAME} shutting down.")


app = FastAPI(
    title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan
)

# CORS is configured deliberately (Section 37) rather than left wide open.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(categories.router)
app.include_router(chat.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Defense-in-depth (Section 35/37): even if a route forgets its own
    try/except, no unhandled exception should ever reach the client as a
    raw stack trace. Routes still handle their own expected exceptions
    (e.g. chat.py's InvalidQueryError -> 400) for a more specific status
    code and message; this only catches whatever slips past that.
    """
    logger.exception(f"Unhandled exception on {request.method} {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."},
    )
