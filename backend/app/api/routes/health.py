"""
Health check endpoint.

Used by deployment platforms, uptime checks, and the frontend to confirm
the backend is reachable before showing the "Online" indicator.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    return {"status": "ok"}
