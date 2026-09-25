"""Router de agent — stub FASE 1."""
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def index():
    return {"message": "Modulo agent — implementado nas proximas fases"}
