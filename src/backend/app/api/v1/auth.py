"""Router de autenticacao — stub FASE 1."""
from fastapi import APIRouter

router = APIRouter()

@router.post("/login")
async def login():
    """Login — implementado na FASE 3."""
    return {"message": "Implementado na FASE 3"}

@router.post("/refresh")
async def refresh():
    """Refresh token — implementado na FASE 3."""
    return {"message": "Implementado na FASE 3"}
