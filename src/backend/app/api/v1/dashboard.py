"""Router de dashboard — stub FASE 1."""
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def index():
    return {"message": "Modulo dashboard — implementado nas proximas fases"}
