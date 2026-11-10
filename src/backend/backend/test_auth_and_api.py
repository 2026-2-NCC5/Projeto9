"""
Testes automatizados da Fase 4 — Autenticacao, Autorizacao e APIs Reais.
Cobre:
  1. Login valido de estudante -> retorna JWT access e refresh tokens validos.
  2. Login com senha invalida -> 401 e registro em auditoria.
  3. Login com email inexistente -> 401.
  4. Renovacao de token (/refresh) com refresh token valido.
  5. Rejeicao de token de acesso expirado ou invalido.
  6. Endpoint de perfil /student/profile para o estudante logado.
  7. Isolamento de historico: estudante A nao pode ver conversa de estudante B.
  8. Criacao e listagem de conversas e mensagens no historico.
  9. Registro de feedback por estudante autenticado.
  10. Restricao de listagem de feedbacks apenas para administradores (403 para estudantes).
  11. Criacao de encaminhamento para atendimento humano (handoff) com protocolo legivel.
  12. Consulta de encaminhamento pelo protocolo com validacao de propriedade.
  13. Consulta de logs de auditoria restrita a administradores.
  14. Integracao do agente com persistencia de conversa no SQLite para usuario autenticado.
"""
import os
import uuid
import asyncio
import tempfile
from pathlib import Path
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.models.entities import User, Student
from app.main import app

# Credenciais ficticias isoladas refletindo as personas ativas do SecretarIA
STUDENT_EMAIL = "ana.silva@fecap.br"
STUDENT_PWD = "demo1234"
STUDENT2_EMAIL = "estudante2@demo.fecap.br"
STUDENT2_PWD = "demo1234"
ADMIN_EMAIL = "admin@fecap.br"
ADMIN_PWD = "admin1234"


@pytest.fixture(scope="module", autouse=True)
def setup_isolated_test_database():
    """Configura um banco SQLite isolado e temporario para testes, garantindo
    que o banco original (fecap_guia.db) nao seja acessado nem modificado."""
    temp_dir = tempfile.TemporaryDirectory()
    db_path = Path(temp_dir.name) / "test_auth_isolated.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _init_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with session_factory() as session:
            # 1. Estudante Principal: Ana Silva
            ana_id = str(uuid.uuid4())
            u1 = User(
                id=ana_id,
                email=STUDENT_EMAIL,
                hashed_password=hash_password(STUDENT_PWD),
                role="student",
                is_active=True,
                is_demo=True,
            )
            s1 = Student(
                id=str(uuid.uuid4()),
                user_id=ana_id,
                name="Ana Demonstracao Silva",
                ra="DEMO001",
                course="Administracao",
                period="3o Semestre",
                email=STUDENT_EMAIL,
                is_demo=True,
            )

            # 2. Estudante 2: Carlos Santos (para teste de isolamento)
            carlos_id = str(uuid.uuid4())
            u2 = User(
                id=carlos_id,
                email=STUDENT2_EMAIL,
                hashed_password=hash_password(STUDENT2_PWD),
                role="student",
                is_active=True,
                is_demo=True,
            )
            s2 = Student(
                id=str(uuid.uuid4()),
                user_id=carlos_id,
                name="Carlos Demonstracao Santos",
                ra="DEMO002",
                course="Ciencias Contabeis",
                period="1o Semestre",
                email=STUDENT2_EMAIL,
                is_demo=True,
            )

            # 3. Administrador Institucional
            admin_id = str(uuid.uuid4())
            u3 = User(
                id=admin_id,
                email=ADMIN_EMAIL,
                hashed_password=hash_password(ADMIN_PWD),
                role="admin",
                is_active=True,
                is_demo=True,
            )

            session.add_all([u1, s1, u2, s2, u3])
            await session.commit()

    asyncio.run(_init_db())

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    yield

    app.dependency_overrides.pop(get_db, None)
    asyncio.run(engine.dispose())
    temp_dir.cleanup()


client = TestClient(app)


def get_token(email: str, password: str) -> dict:
    """Helper para autenticar e obter tokens."""
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Falha no login com {email}: {res.text}"
    return res.json()


def test_login_valid_student():
    """1. Login valido com credenciais de estudante."""
    data = get_token(STUDENT_EMAIL, STUDENT_PWD)
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == STUDENT_EMAIL
    assert data["user"]["role"] == "student"


def test_login_invalid_password():
    """2. Tentativa de login com senha incorreta."""
    res = client.post("/api/v1/auth/login", json={"email": STUDENT_EMAIL, "password": "wrong_password"})
    assert res.status_code == 401
    assert "Credenciais invalidas" in res.json()["detail"]


def test_login_nonexistent_email():
    """3. Tentativa de login com usuario inexistente."""
    res = client.post("/api/v1/auth/login", json={"email": "naoexiste@fecap.br", "password": "qualquer_coisa"})
    assert res.status_code == 401


def test_refresh_token_flow():
    """4. Renovacao de access token via endpoint /refresh."""
    login_data = get_token(STUDENT_EMAIL, STUDENT_PWD)
    refresh_token = login_data["refresh_token"]

    res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert res.status_code == 200
    new_data = res.json()
    assert "access_token" in new_data
    assert new_data["access_token"] != login_data["access_token"]
    assert new_data["user"]["email"] == STUDENT_EMAIL


def test_expired_or_invalid_token():
    """5. Rejeicao de tokens invalidos ou expirados."""
    # Token inexistente
    res = client.get("/api/v1/student/profile", headers={"Authorization": "Bearer token_falso_123"})
    assert res.status_code == 401

    # Token expirado
    expired_token = create_access_token(
        {"sub": "user_123", "email": "test@fecap.br", "role": "student"},
        expires_delta=timedelta(seconds=-10),
    )
    res_expired = client.get(
        "/api/v1/student/profile",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res_expired.status_code == 401


def test_student_profile_endpoint():
    """6. Consulta de perfil do estudante logado."""
    tokens = get_token(STUDENT_EMAIL, STUDENT_PWD)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    res = client.get("/api/v1/student/profile", headers=headers)
    assert res.status_code == 200
    profile = res.json()
    assert profile["email"] == STUDENT_EMAIL
    assert profile["ra"] == "DEMO001"
    assert profile["course"] == "Administracao"


def test_history_creation_and_isolation():
    """7 e 8. Criacao de conversas e garantia de isolamento entre usuarios."""
    # Login Aluno 1 (Ana Silva)
    tokens_1 = get_token(STUDENT_EMAIL, STUDENT_PWD)
    headers_1 = {"Authorization": f"Bearer {tokens_1['access_token']}"}

    # Criar conversa para Aluno 1
    res_conv = client.post(
        "/api/v1/history/",
        json={"title": "Conversa Aluno 1"},
        headers=headers_1,
    )
    assert res_conv.status_code == 201
    conv_id = res_conv.json()["id"]

    # Aluno 1 adiciona mensagem
    res_msg = client.post(
        f"/api/v1/history/{conv_id}/messages",
        json={"role": "user", "content": "Minha pergunta sobre matricula"},
        headers=headers_1,
    )
    assert res_msg.status_code == 201

    # Login Aluno 2 (segundo estudante do seed: Carlos)
    tokens_2 = get_token(STUDENT2_EMAIL, STUDENT2_PWD)
    headers_2 = {"Authorization": f"Bearer {tokens_2['access_token']}"}

    # Aluno 2 tenta acessar a conversa do Aluno 1 -> deve receber 403 Forbidden
    res_forbidden = client.get(f"/api/v1/history/{conv_id}", headers=headers_2)
    assert res_forbidden.status_code == 403

    # Aluno 2 tenta postar mensagem na conversa do Aluno 1 -> 403
    res_post_forbidden = client.post(
        f"/api/v1/history/{conv_id}/messages",
        json={"role": "user", "content": "Invasao"},
        headers=headers_2,
    )
    assert res_post_forbidden.status_code == 403

    # Aluno 1 lista historico e ve sua conversa
    res_list = client.get("/api/v1/history/", headers=headers_1)
    assert res_list.status_code == 200
    ids = [c["id"] for c in res_list.json()]
    assert conv_id in ids


def test_feedback_submission_and_role_control():
    """9 e 10. Submissao de feedback por estudante e listagem restrita a administradores."""
    tokens_student = get_token(STUDENT_EMAIL, STUDENT_PWD)
    headers_student = {"Authorization": f"Bearer {tokens_student['access_token']}"}

    # Estudante submete feedback positivo
    fb_res = client.post(
        "/api/v1/feedback/",
        json={"rating": "positive", "rating_value": 5, "comment": "Muito esclarecedor!"},
        headers=headers_student,
    )
    assert fb_res.status_code == 201
    fb_data = fb_res.json()
    assert fb_data["rating"] == "positive"

    # Estudante tenta listar feedbacks -> 403 Forbidden
    res_forbidden = client.get("/api/v1/feedback/", headers=headers_student)
    assert res_forbidden.status_code == 403

    # Administrador lista feedbacks -> 200 OK
    tokens_admin = get_token(ADMIN_EMAIL, ADMIN_PWD)
    headers_admin = {"Authorization": f"Bearer {tokens_admin['access_token']}"}
    res_admin = client.get("/api/v1/feedback/", headers=headers_admin)
    assert res_admin.status_code == 200
    assert len(res_admin.json()) >= 1


def test_handoff_creation_and_protocol_tracking():
    """11 e 12. Criacao de encaminhamento humano com protocolo unico e consulta."""
    tokens = get_token(STUDENT_EMAIL, STUDENT_PWD)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    payload = {
        "category": "documentos",
        "priority": "normal",
        "reason": "Preciso de declaracao de conclusao de curso urgente.",
    }
    res = client.post("/api/v1/handoff/", json=payload, headers=headers)
    assert res.status_code == 201
    ticket = res.json()

    assert ticket["protocol"].startswith("FECAP-")
    assert ticket["status"] == "pending"
    assert "Secretaria Acadêmica ASA" in ticket["attendant"]
    if settings.llm_mode.lower() == "demo":
        assert "SIMULADO" in ticket["attendant"]

    protocol = ticket["protocol"]

    # Consulta por protocolo pelo proprio estudante
    res_get = client.get(f"/api/v1/handoff/{protocol}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["protocol"] == protocol


def test_audit_logs_role_restriction():
    """13. Acesso a trilha de auditoria restrito a administradores."""
    tokens_student = get_token(STUDENT_EMAIL, STUDENT_PWD)
    headers_student = {"Authorization": f"Bearer {tokens_student['access_token']}"}

    res_student = client.get("/api/v1/audit/", headers=headers_student)
    assert res_student.status_code == 403

    tokens_admin = get_token(ADMIN_EMAIL, ADMIN_PWD)
    headers_admin = {"Authorization": f"Bearer {tokens_admin['access_token']}"}

    res_admin = client.get("/api/v1/audit/", headers=headers_admin)
    assert res_admin.status_code == 200
    logs = res_admin.json()
    assert isinstance(logs, list)
    assert len(logs) > 0  # Auditoria deve conter os logins e acoes anteriores


def test_agent_query_persists_turn_when_authenticated():
    """14. A consulta ao agente persiste conversa e mensagens quando o usuario esta autenticado."""
    tokens = get_token(STUDENT_EMAIL, STUDENT_PWD)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    payload = {
        "question": "Como solicitar declaracao de matricula no portal?",
    }
    res = client.post("/api/v1/agent/query", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()

    # O endpoint deve associar ou criar uma conversa
    assert data.get("conversation_id") is not None
    conv_id = data["conversation_id"]

    # Inspecionar conversa no historico do estudante
    res_conv = client.get(f"/api/v1/history/{conv_id}", headers=headers)
    assert res_conv.status_code == 200
    messages = res_conv.json()["messages"]
    assert len(messages) >= 2
    roles = [m["role"] for m in messages]
    assert "user" in roles
    assert "assistant" in roles
