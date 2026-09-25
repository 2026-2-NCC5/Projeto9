"""
Configuracao do banco de dados SQLAlchemy.
Suporta SQLite (dev) e PostgreSQL (prod) via DATABASE_URL.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


# Adaptar URL para driver async
def get_async_url(url: str) -> str:
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///")
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://")
    return url


ASYNC_DATABASE_URL = get_async_url(settings.database_url)

engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=settings.debug,
    connect_args={"check_same_thread": False} if "sqlite" in ASYNC_DATABASE_URL else {}
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """Dependency injection para sessoes de banco."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """Cria todas as tabelas (usado em desenvolvimento)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
