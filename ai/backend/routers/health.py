"""Router untuk health check endpoint layanan ai-backend. Keyword: backend API."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "ai-backend"}