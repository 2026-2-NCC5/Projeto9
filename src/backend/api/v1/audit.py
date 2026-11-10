"""
Router de Auditoria de Seguranca.
Exclusivo para administradores: consulta trilha de auditoria do sistema,
com mascaramento de eventuais segredos, tokens ou senhas.
"""
import re
from typing import List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.entities import AuditLog, User
from app.schemas.schemas import AuditLogResponse

router = APIRouter()

_SECRET_PATTERN = re.compile(
    r"(password|senha|secret|token|bearer|api_key)\s*[:=]\s*([^\s,;]+)",
    re.IGNORECASE,
)


def sanitize_detail(detail: Optional[str]) -> Optional[str]:
    """Garante que nenhum token, senha ou segredo seja exposto nos detalhes de auditoria."""
    if not detail:
        return detail
    return _SECRET_PATTERN.sub(r"\1=[REDACTED]", detail)


@router.get("/", response_model=List[AuditLogResponse], status_code=status.HTTP_200_OK)
async def list_audit_logs(
    action: Optional[str] = None,
    resource: Optional[str] = None,
    limit: int = 100,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> List[AuditLogResponse]:
    """Lista registros de auditoria em ordem cronologica reversa."""
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if resource:
        stmt = stmt.where(AuditLog.resource == resource)
    stmt = stmt.limit(min(limit, 500))

    result = await db.execute(stmt)
    logs = result.scalars().all()

    items: List[AuditLogResponse] = []
    for log in logs:
        validated = AuditLogResponse.model_validate(log)
        validated.detail = sanitize_detail(validated.detail)
        items.append(validated)
    return items

