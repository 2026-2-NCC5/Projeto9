"""Router de knowledge — stub FASE 1."""
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def index():
    return {"message": "Modulo knowledge — implementado nas proximas fases"}
