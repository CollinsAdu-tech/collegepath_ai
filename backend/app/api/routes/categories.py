"""
GET /categories — returns the FAQ categories available in the knowledge
base (Section 25). Used by the frontend for category chips (Section 31)
and general navigation; static enough that it reads straight from the
already-loaded, in-memory knowledge base rather than touching disk.
"""

from fastapi import APIRouter, Request

from app.models.schemas import CategoriesResponse

router = APIRouter()


@router.get("/categories", response_model=CategoriesResponse)
def get_categories(request: Request) -> CategoriesResponse:
    knowledge_base = request.app.state.knowledge_base
    return CategoriesResponse(categories=knowledge_base.categories)
