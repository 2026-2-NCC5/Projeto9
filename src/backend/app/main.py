"""
FECAP Guia — Ponto de entrada da API FastAPI.

AVISO: Este e um projeto academico de demonstracao.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.database import create_tables
from app.api.router import api_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Eventos de startup e shutdown."""
    configure_logging()
    logger.info("Iniciando FECAP Guia", version=settings.app_version, mode=settings.llm_mode)
    
    # Criar tabelas se nao existirem (apenas dev — em prod use alembic)
    if settings.app_env == "development":
        await create_tables()
    
    yield
    
    logger.info("Encerrando FECAP Guia")


app = FastAPI(
    title="FECAP Guia API",
    description=(
        "Agente Inteligente de Orientacao ao Estudante — FECAP\\n\\n"
        "> **AVISO**: Este e um projeto academico de demonstracao. "
        "Dados sao ficticios."
    ),
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ----- CORS -----
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- Routers -----
app.include_router(api_router, prefix="/api/v1")


# ----- Health Check -----
@app.get("/health", tags=["System"])
async def health_check():
    """Verifica saude da aplicacao."""
    return {
        "status": "ok",
        "version": settings.app_version,
        "env": settings.app_env,
        "llm_mode": settings.llm_mode,
        "demo_mode": True,  # Sempre verdadeiro para demonstracao
    }


# ----- Root -----
@app.get("/", tags=["System"])
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
        "notice": "Projeto academico de demonstracao — dados ficticios",
    }


# ----- Exception handlers -----
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error("Erro nao tratado", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor. Tente novamente."}
    )
