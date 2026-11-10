"""
Modelos SQLAlchemy para o FECAP Guia.
Compatível com SQLite (aiosqlite) e PostgreSQL (asyncpg).
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    String,
    Text,
    Boolean,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="student", nullable=False)  # student | admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relacionamentos
    student_profile: Mapped[Optional["Student"]] = relationship("Student", back_populates="user", uselist=False, cascade="all, delete-orphan")
    conversations: Mapped[List["Conversation"]] = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")


class Student(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ra: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    course: Mapped[str] = mapped_column(String(255), nullable=False)
    period: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relacionamento
    user: Mapped[Optional["User"]] = relationship("User", back_populates="student_profile")


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    origin: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), default="1.0-DEMO", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)  # active | inactive | draft
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    chunks_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(255), default="Secretaria", nullable=True)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relacionamentos
    user: Mapped[Optional["User"]] = relationship("User", back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    handoffs: Mapped[List["HandoffTicket"]] = relationship("HandoffTicket", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant | system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Metadados do Agente RAG (quando role == 'assistant')
    steps: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # List[str]
    next_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    document_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    evidence: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # List[AgentEvidence]
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    requires_human: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relacionamentos
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
    feedbacks: Mapped[List["Feedback"]] = relationship("Feedback", back_populates="message", cascade="all, delete-orphan")


class Feedback(Base):
    __tablename__ = "feedbacks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    message_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("messages.id", ondelete="CASCADE"), index=True, nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    rating: Mapped[str] = mapped_column(String(20), nullable=False)  # positive | negative ou 1-5
    rating_value: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1 a 5 numérico
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relacionamento
    message: Mapped[Optional["Message"]] = relationship("Message", back_populates="feedbacks")


class HandoffTicket(Base):
    __tablename__ = "handoff_tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    protocol: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    conversation_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("conversations.id", ondelete="SET NULL"), index=True, nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="academico", nullable=False)  # academico | financeiro | documentos | portal | outro
    priority: Mapped[str] = mapped_column(String(20), default="normal", nullable=False)    # normal | priority | urgent
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)     # pending | in_progress | resolved | transferred
    attendant: Mapped[Optional[str]] = mapped_column(String(255), default="Secretaria Acadêmica ASA", nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relacionamento
    conversation: Mapped[Optional["Conversation"]] = relationship("Conversation", back_populates="handoffs")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    resource: Mapped[str] = mapped_column(String(100), nullable=False)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relacionamento
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")


class HumanValidation(Base):
    """
    RF08 — Validação Humana de Respostas do Agente.
    Registra confirmação, ajuste, rejeição ou complementação de respostas da IA por administradores.
    """
    __tablename__ = "human_validations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    message_id: Mapped[str] = mapped_column(String(36), ForeignKey("messages.id", ondelete="CASCADE"), index=True, nullable=False)
    reviewer_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=False)
    decision: Mapped[str] = mapped_column(String(50), nullable=False)  # confirm | adjust | reject | complement
    justification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    adjusted_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    classification: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    response_version: Mapped[str] = mapped_column(String(50), default="1.0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)



class Boleto(Base):
    """Boleto FICTICIO de demonstracao (sem valor financeiro ou bancario)."""
    __tablename__ = "boletos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False)
    competence: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pendente", nullable=False)  # pendente | pago
    document_id: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

