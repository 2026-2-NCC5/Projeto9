"""Router de audit — stub FASE 1."""
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def index():
    return {"message": "Modulo audit — implementado nas proximas fases"}
