"""
Router de autenticacao: Login e Refresh Token.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import record_audit_log
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.entities import User
from app.schemas.schemas import LoginRequest, RefreshRequest, TokenResponse, UserResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Autentica o usuario via email/senha e retorna access e refresh tokens."""
    stmt = (
        select(User)
        .options(selectinload(User.student_profile))
        .where(User.email == payload.email)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        # Registrar tentativa falha em auditoria
        await record_audit_log(
            db=db,
            action="login_failed",
            resource="auth",
            detail=f"Tentativa de login falhou para email: {payload.email}",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais invalidas.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inativo.",
        )

    token_data = {"sub": user.id, "email": user.email, "role": user.role}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Registrar login bem-sucedido
    await record_audit_log(
        db=db,
        action="login_success",
        resource="auth",
        detail=f"Usuario {user.email} autenticado com role {user.role}",
        user_id=user.id,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Gera um novo access token a partir de um refresh token valido."""
    decoded = decode_token(payload.refresh_token)
    if not decoded or decoded.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = decoded.get("sub")
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
            detail="Usuario nao encontrado ou inativo.",
        )

    token_data = {"sub": user.id, "email": user.email, "role": user.role}
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    await record_audit_log(
        db=db,
        action="token_refresh",
        resource="auth",
        detail=f"Token renovado para usuario {user.email}",
        user_id=user.id,
    )

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )
