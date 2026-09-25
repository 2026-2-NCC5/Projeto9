"""Router de estudante — stub FASE 1."""
from fastapi import APIRouter

router = APIRouter()

@router.get("/profile")
async def get_profile():
    """Perfil do estudante — implementado na FASE 3."""
    return {"message": "Implementado na FASE 3"}
