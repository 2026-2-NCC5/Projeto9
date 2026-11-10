"""
Dependencias FastAPI para autenticacao, autorizacao e auditoria.
Centraliza extracao do usuario autenticado a partir de tokens JWT.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import decode_token
from app.models.entities import User, Student, AuditLog

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extrai e valida o usuario logado pelo JWT Bearer token."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticacao necessaria.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso invalido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tipo de token invalido. Esperado access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token malformado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = (
        select(User)
        .options(selectinload(User.student_profile))
        .where(User.id == user_id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inativo ou inexistente.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Retorna o usuario se o token for valido; caso contrario, None."""
    if not credentials or not credentials.credentials:
        return None
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


async def require_student(user: User = Depends(get_current_user)) -> User:
    """Valida se o usuario possui perfil de estudante ou admin."""
    if user.role not in ["student", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso permitido apenas para estudantes.",
        )
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Valida se o usuario possui perfil de administrador."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito para administradores.",
        )
    return user


async def record_audit_log(
    db: AsyncSession,
    action: str,
    resource: str,
    detail: Optional[str] = None,
    user_id: Optional[str] = None,
) -> AuditLog:
    """Registra uma entrada na tabela de auditoria."""
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        detail=detail,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log
