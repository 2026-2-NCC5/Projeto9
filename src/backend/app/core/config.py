"""
Configuracao central da aplicacao.
Lida com variaveis de ambiente via pydantic-settings.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    # Aplicacao
    app_name: str = Field(default="FECAP Guia", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    app_env: str = Field(default="development", env="APP_ENV")
    debug: bool = Field(default=True, env="DEBUG")

    # Banco de dados
    database_url: str = Field(
        default="sqlite:///./fecap_guia.db",
        env="DATABASE_URL"
    )

    # JWT
    secret_key: str = Field(env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=60, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")

    # Agente
    llm_mode: str = Field(default="demo", env="LLM_MODE")  # demo | gemini
    google_api_key: str = Field(default="", env="GOOGLE_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", env="GEMINI_MODEL")

    # Parametros do agente
    agent_temperature: float = Field(default=0.1, env="AGENT_TEMPERATURE")
    agent_max_tokens: int = Field(default=2048, env="AGENT_MAX_TOKENS")
    agent_top_k_documents: int = Field(default=5, env="AGENT_TOP_K_DOCUMENTS")
    agent_confidence_threshold: float = Field(default=0.4, env="AGENT_CONFIDENCE_THRESHOLD")
    agent_min_evidence_score: float = Field(default=0.35, env="AGENT_MIN_EVIDENCE_SCORE")
    agent_version: str = Field(default="1.0.0", env="AGENT_VERSION")
    agent_fallback_message: str = Field(
        default="Nao encontrei informacao oficial suficiente na base de conhecimento "
                "para responder com seguranca. Recomendo encaminhar sua solicitacao "
                "para atendimento humano.",
        env="AGENT_FALLBACK_MESSAGE"
    )

    # Embeddings
    embedding_model: str = Field(default="all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
    embedding_device: str = Field(default="cpu", env="EMBEDDING_DEVICE")

    # ChromaDB
    chroma_persist_directory: str = Field(default="./chroma_db", env="CHROMA_PERSIST_DIRECTORY")
    chroma_collection_name: str = Field(default="fecap_knowledge", env="CHROMA_COLLECTION_NAME")

    # Importacao
    max_document_size_mb: int = Field(default=10, env="MAX_DOCUMENT_SIZE_MB")
    allowed_document_types: str = Field(default="pdf,txt,docx", env="ALLOWED_DOCUMENT_TYPES")
    chunk_size: int = Field(default=500, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=50, env="CHUNK_OVERLAP")

    # CORS
    backend_cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        env="BACKEND_CORS_ORIGINS"
    )

    # Logs
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # Auditoria
    audit_retention_days: int = Field(default=365, env="AUDIT_RETENTION_DAYS")

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",")]

    @property
    def allowed_types_list(self) -> List[str]:
        return [t.strip() for t in self.allowed_document_types.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
