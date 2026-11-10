"""
Schemas Pydantic para validação e serialização de dados no FECAP Guia.
Compatível com a API FastAPI e com os tipos TypeScript do frontend.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ==========================================
# Autenticação e Usuário
# ==========================================

class UserBase(BaseModel):
    email: EmailStr
    role: str = "student"


class UserCreate(UserBase):
    password: str = Field(min_length=6)
    is_demo: bool = False


class UserResponse(UserBase):
    id: str
    is_active: bool
    is_demo: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


# ==========================================
# Perfil do Estudante
# ==========================================

class StudentBase(BaseModel):
    name: str
    ra: str
    course: str
    period: str
    email: EmailStr


class StudentCreate(StudentBase):
    user_id: Optional[str] = None
    is_demo: bool = False


class StudentResponse(StudentBase):
    id: str
    user_id: Optional[str] = None
    is_demo: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Documentos da Base de Conhecimento
# ==========================================

class KnowledgeDocumentBase(BaseModel):
    title: str
    category: str
    origin: str
    version: str = "1.0-DEMO"
    status: str = "active"
    file_path: Optional[str] = None
    chunks_count: int = 0
    is_demo: bool = True


class KnowledgeDocumentCreate(KnowledgeDocumentBase):
    content: Optional[str] = None
    created_by: Optional[str] = "Secretaria"


class KnowledgeDocumentUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    origin: Optional[str] = None
    version: Optional[str] = None
    status: Optional[str] = None
    content: Optional[str] = None


class KnowledgeDocumentResponse(KnowledgeDocumentBase):
    id: str
    published_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class KnowledgeDocumentDetailResponse(KnowledgeDocumentResponse):
    content: Optional[str] = None


# ==========================================
# Agente RAG, Mensagens e Conversas
# ==========================================

class AgentQuery(BaseModel):
    question: str
    student_id: Optional[str] = None
    conversation_id: Optional[str] = None


class AgentEvidence(BaseModel):
    chunk: str
    document: str
    relevance_score: Optional[float] = None


class AgentResponse(BaseModel):
    id: Optional[str] = None
    conversation_id: Optional[str] = None
    answer: str

    steps: Optional[List[str]] = None
    next_action: Optional[str] = None
    source: Optional[str] = None
    version: Optional[str] = None
    updated_at: Optional[str] = None
    evidence: Optional[List[AgentEvidence]] = None
    confidence: Optional[float] = None
    requires_human: bool = False


class MessageCreate(BaseModel):
    role: str
    content: str
    steps: Optional[List[str]] = None
    next_action: Optional[str] = None
    source: Optional[str] = None
    document_version: Optional[str] = None
    evidence: Optional[List[dict]] = None
    confidence: Optional[float] = None
    requires_human: bool = False


from pydantic import field_validator
from typing import Any, Union


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    steps: Optional[Union[List[str], dict]] = None
    next_action: Optional[str] = None
    source: Optional[str] = None
    document_version: Optional[str] = None
    evidence: Optional[List[dict]] = None
    confidence: Optional[float] = None
    requires_human: bool
    created_at: datetime

    @field_validator("steps", mode="before")
    @classmethod
    def normalize_steps(cls, v: Any) -> Any:
        if isinstance(v, dict) and "steps" in v:
            return v["steps"]
        return v

    model_config = ConfigDict(from_attributes=True)



class ConversationCreate(BaseModel):
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Feedback
# ==========================================

class FeedbackCreate(BaseModel):
    message_id: Optional[str] = None
    rating: str = Field(description="positive | negative ou 1-5")
    rating_value: Optional[int] = Field(default=None, ge=1, le=5)
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: str
    message_id: Optional[str] = None
    user_id: Optional[str] = None
    rating: str
    rating_value: Optional[int] = None
    comment: Optional[str] = None
    question_context: Optional[str] = None
    answer_context: Optional[str] = None
    needs_review: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Encaminhamento Humano (Handoff)
# ==========================================

class HandoffCreate(BaseModel):
    conversation_id: Optional[str] = None
    category: str = Field(default="academico", description="academico | financeiro | documentos | portal | outro")
    priority: str = Field(default="normal", description="normal | priority | urgent")
    reason: str
    summary: Optional[str] = None


class HandoffUpdate(BaseModel):
    status: Optional[str] = None
    attendant: Optional[str] = None
    summary: Optional[str] = None
    priority: Optional[str] = None


class HandoffResponse(BaseModel):
    id: str
    protocol: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    category: str
    priority: str
    reason: str
    summary: Optional[str] = None
    status: str
    attendant: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Validação Humana (RF08) e Abstenções
# ==========================================

class HumanValidationCreate(BaseModel):
    message_id: str
    decision: str = Field(description="confirm | adjust | reject | complement")
    justification: Optional[str] = None
    adjusted_answer: Optional[str] = None
    classification: Optional[str] = None
    response_version: str = "1.0"


class HumanValidationResponse(BaseModel):
    id: str
    message_id: str
    reviewer_id: str
    decision: str
    justification: Optional[str] = None
    adjusted_answer: Optional[str] = None
    classification: Optional[str] = None
    response_version: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UnansweredQuestionItem(BaseModel):
    message_id: str
    conversation_id: str
    question: str
    agent_answer: str
    confidence: float
    created_at: datetime
    validation_status: str = "pending"
    validation_decision: Optional[str] = None
    classification: Optional[str] = None
    justification: Optional[str] = None


# ==========================================
# Dashboard Admin
# ==========================================

class CategoryCountItem(BaseModel):
    category: str
    count: int


class DailyQuestionCountItem(BaseModel):
    date: str
    count: int


class DashboardMetricsResponse(BaseModel):
    total_questions: int
    total_answers: int
    answers_with_evidence_rate: float
    positive_feedback_rate: float
    handoffs_count: int
    unanswered_count: int
    avg_response_time_ms: int
    active_documents_count: int = 0
    validations_count: int = 0
    top_categories: List[CategoryCountItem] = []
    questions_per_day: List[DailyQuestionCountItem] = []


# ==========================================
# Auditoria
# ==========================================

class AuditLogCreate(BaseModel):
    action: str
    resource: str
    detail: Optional[str] = None


class AuditLogResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    action: str
    resource: str
    detail: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

