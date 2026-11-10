"""
Modelos SQLAlchemy do FECAP Guia.
Exporta todos os modelos para registro central no Base.metadata.
"""
from app.models.entities import (
    User,
    Student,
    KnowledgeDocument,
    Conversation,
    Message,
    Feedback,
    HandoffTicket,
    AuditLog,
    HumanValidation,
    Boleto,
    generate_uuid,
    utc_now,
)

__all__ = [
    "User",
    "Student",
    "KnowledgeDocument",
    "Conversation",
    "Message",
    "Feedback",
    "HandoffTicket",
    "AuditLog",
    "HumanValidation",
    "Boleto",
    "generate_uuid",
    "utc_now",
]

