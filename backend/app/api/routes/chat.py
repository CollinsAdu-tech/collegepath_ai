"""
POST /chat — the chatbot's main endpoint.

This route is deliberately thin: it validates the transport-level shape
of the request (via ChatRequest), delegates all real work to
ChatbotService.answer_query(), and translates the one business-rule
exception that service can raise (InvalidQueryError) into a clean HTTP
error. No retrieval, threshold, or formatting logic belongs here.
"""

from fastapi import APIRouter, HTTPException, Request

from app.core.exceptions import InvalidQueryError
from app.models.schemas import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, request: Request) -> ChatResponse:
    chatbot_service = request.app.state.chatbot_service

    try:
        return chatbot_service.answer_query(body.message)
    except InvalidQueryError as exc:
        # Section 26/37: a bad query is a client error (400), and the
        # message should explain what's wrong without leaking internals.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
