"""Router de feedback — stub FASE 1."""
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def index():
    return {"message": "Modulo feedback — implementado nas proximas fases"}
