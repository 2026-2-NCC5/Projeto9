"""
Testes de integracao e persistencia SQLite para o FECAP Guia.
Valida criacao de tabelas, modelos SQLAlchemy, relacionamentos e persistencia dos dados.
"""
import os
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import Base
from app.models import (
    User,
    Student,
    KnowledgeDocument,
    Conversation,
    Message,
    Feedback,
    HandoffTicket,
    AuditLog,
)
from app.core.security import hash_password, verify_password


TEST_DB_FILE = "./test_fecap_guia.db"
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE}"


@pytest_asyncio.fixture
async def async_test_session():
    """Cria banco isolado de teste, tabelas e fornece sessao assincrona."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass


@pytest.mark.asyncio
async def test_create_user_and_student_profile(async_test_session: AsyncSession):
    """Testa insercao de usuario e perfil de estudante associado com eager loading assincrono."""
    plain_pw = "alunoFecap2026!"
    hashed_pw = hash_password(plain_pw)
    assert verify_password(plain_pw, hashed_pw) is True

    user = User(
        email="estudante_teste@demo.fecap.br",
        hashed_password=hashed_pw,
        role="student",
        is_demo=True,
    )
    async_test_session.add(user)
    await async_test_session.flush()

    student = Student(
        user_id=user.id,
        name="Estudante Teste de Integracao",
        ra="RA-998877",
        course="Ciencia da Computacao",
        period="4o Semestre",
        email="estudante_teste@demo.fecap.br",
        is_demo=True,
    )
    async_test_session.add(student)
    await async_test_session.commit()

    # Consulta com relacionamento carregado explicitamente via selectinload
    stmt = (
        select(User)
        .options(selectinload(User.student_profile))
        .where(User.email == "estudante_teste@demo.fecap.br")
    )
    result = await async_test_session.execute(stmt)
    saved_user = result.scalar_one_or_none()

    assert saved_user is not None
    assert saved_user.email == "estudante_teste@demo.fecap.br"
    assert saved_user.student_profile is not None
    assert saved_user.student_profile.ra == "RA-998877"
    assert saved_user.student_profile.course == "Ciencia da Computacao"


@pytest.mark.asyncio
async def test_conversation_messages_and_feedback(async_test_session: AsyncSession):
    """Testa persistencia de conversa, mensagem com metadados RAG e avaliacao de feedback."""
    conv = Conversation(title="Duvida sobre trancamento")
    async_test_session.add(conv)
    await async_test_session.flush()

    # Pergunta do aluno
    msg_user = Message(
        conversation_id=conv.id,
        role="user",
        content="Como faco para trancar o semestre?",
        requires_human=False,
    )
    async_test_session.add(msg_user)

    # Resposta do Agente RAG com metadados estruturados
    msg_agent = Message(
        conversation_id=conv.id,
        role="assistant",
        content="O trancamento pode ser realizado pelo Portal do Aluno em ate 30 dias.",
        steps=["Acesse o portal", "Va em requerimentos", "Selecione trancamento"],
        next_action="Acessar o Portal do Aluno",
        source="Regimento Geral FECAP",
        document_version="1.0-DEMO",
        evidence=[{"chunk": "Artigo 12...", "document": "Regimento"}],
        confidence=0.88,
        requires_human=False,
    )
    async_test_session.add(msg_agent)
    await async_test_session.flush()

    # Feedback do aluno
    fb = Feedback(
        message_id=msg_agent.id,
        rating="positive",
        rating_value=5,
        comment="Instrucao muito clara e rapida!",
    )
    async_test_session.add(fb)
    await async_test_session.commit()

    # Validacao no banco com carregamento antecipado de mensagens e feedbacks
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.messages).selectinload(Message.feedbacks))
        .where(Conversation.id == conv.id)
    )
    result = await async_test_session.execute(stmt)
    saved_conv = result.scalar_one()

    assert len(saved_conv.messages) == 2
    assert saved_conv.messages[1].confidence == 0.88
    assert len(saved_conv.messages[1].steps) == 3
    assert len(saved_conv.messages[1].feedbacks) == 1
    assert saved_conv.messages[1].feedbacks[0].rating == "positive"
    assert saved_conv.messages[1].feedbacks[0].rating_value == 5


@pytest.mark.asyncio
async def test_handoff_and_audit_persistence(async_test_session: AsyncSession):
    """Testa abertura de protocolo de encaminhamento humano e log de auditoria."""
    protocol_num = "PROT-2026-TEST-777"
    ticket = HandoffTicket(
        protocol=protocol_num,
        category="financeiro",
        priority="urgent",
        reason="Divergencia no boleto de rematricula",
        summary="Aluno solicitou verificacao financeira de bolsa",
        status="pending",
    )
    async_test_session.add(ticket)

    audit = AuditLog(
        action="HANDOFF_CREATED",
        resource="handoff_tickets",
        detail=f"Criado protocolo {protocol_num} com prioridade urgente",
    )
    async_test_session.add(audit)
    await async_test_session.commit()

    stmt_t = select(HandoffTicket).where(HandoffTicket.protocol == protocol_num)
    res_t = await async_test_session.execute(stmt_t)
    saved_ticket = res_t.scalar_one_or_none()

    assert saved_ticket is not None
    assert saved_ticket.priority == "urgent"
    assert saved_ticket.status == "pending"

    stmt_a = select(AuditLog).where(AuditLog.action == "HANDOFF_CREATED")
    res_a = await async_test_session.execute(stmt_a)
    saved_audit = res_a.scalar_one_or_none()

    assert saved_audit is not None
    assert "PROT-2026-TEST-777" in saved_audit.detail


@pytest.mark.asyncio
async def test_knowledge_documents_persistence(async_test_session: AsyncSession):
    """Testa armazenamento dos documentos da base de conhecimento ficticia."""
    doc = KnowledgeDocument(
        title="Regulamento de Atividades Complementares",
        category="atendimento_academico",
        origin="Secretaria Geral",
        version="1.0-DEMO",
        status="active",
        content="As horas complementares devem ser entregues no ultimo semestre.",
        chunks_count=1,
        is_demo=True,
    )
    async_test_session.add(doc)
    await async_test_session.commit()

    stmt = select(KnowledgeDocument).where(KnowledgeDocument.title == "Regulamento de Atividades Complementares")
    res = await async_test_session.execute(stmt)
    saved_doc = res.scalar_one_or_none()

    assert saved_doc is not None
    assert saved_doc.is_demo is True
    assert saved_doc.status == "active"
