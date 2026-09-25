"""Router de history — stub FASE 1."""
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def index():
    return {"message": "Modulo history — implementado nas proximas fases"}
