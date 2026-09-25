"""Router de handoff — stub FASE 1."""
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def index():
    return {"message": "Modulo handoff — implementado nas proximas fases"}
