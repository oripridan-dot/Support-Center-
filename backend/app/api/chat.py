from fastapi import APIRouter, Depends
from pydantic import BaseModel
from ..services.rag_service import ask_question

router = APIRouter()

class ChatRequest(BaseModel):
    question: str
    brand_id: int | None = None
    product_id: int | None = None
    is_first_message: bool = False
    history: list[dict] = []

class ChatResponse(BaseModel):
    answer: str
    sources: list
    images: list[dict] = []
    pdfs: list[dict] = []
    brand_logos: list[dict] = []

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # In the future, we will pass the brand_id to filter the context
    response = await ask_question(
        request.question, 
        request.brand_id, 
        request.is_first_message,
        request.history,
        request.product_id
    )
    return response
