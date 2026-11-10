"""
Testes automatizados da Fase 6 — Integração do Painel Administrativo FECAP Guia.
Cobre:
  1. Dashboard real (/api/v1/dashboard/) e restrição RBAC (403 para estudante).
  2. Base de Conhecimento: listagem, criação, edição, versionamento, desativação e sincronização ChromaDB sem duplicação.
  3. Upload autorizado de documento TXT/PDF e validação de formato/conteúdo.
  4. Dúvidas não respondidas (/api/v1/agent/unanswered) e revisão administrativa.
  5. Validação Humana RF08 (/api/v1/agent/validations): confirmar, ajustar, rejeitar, complementar, exigência de justificativa e versionamento da resposta.
  6. Atualização de Encaminhamento Humano (PATCH /api/v1/handoff/{protocol}) e registro em auditoria.
  7. Auditoria (/api/v1/audit/) com mascaramento de segredos e restrição RBAC.
"""
import asyncio
import io
from fastapi.testclient import TestClient

from app.core.database import create_tables
from app.knowledge.vector_store import VectorStoreService
from app.main import app

# Garante que a nova tabela human_validations exista no SQLite antes dos testes
asyncio.run(create_tables())

client = TestClient(app)

STUDENT_EMAIL = "estudante@demo.fecap.br"
STUDENT_PWD = "demo1234"
ADMIN_EMAIL = "admin@demo.fecap.br"
ADMIN_PWD = "admin1234"


def get_headers(email: str, password: str) -> dict:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login falhou para {email}: {res.text}"
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_dashboard_metrics_and_rbac():
    """1. Dashboard retorna métricas reais para admin e bloqueia estudante (403)."""
    student_headers = get_headers(STUDENT_EMAIL, STUDENT_PWD)
    res_forbidden = client.get("/api/v1/dashboard/", headers=student_headers)
    assert res_forbidden.status_code == 403

    admin_headers = get_headers(ADMIN_EMAIL, ADMIN_PWD)
    res = client.get("/api/v1/dashboard/", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()

    assert "total_questions" in data
    assert "answers_with_evidence_rate" in data
    assert "positive_feedback_rate" in data
    assert "handoffs_count" in data
    assert "unanswered_count" in data
    assert "active_documents_count" in data
    assert data["active_documents_count"] >= 8
    assert isinstance(data["top_categories"], list)
    assert isinstance(data["questions_per_day"], list)


def test_knowledge_crud_versioning_and_chromadb_sync():
    """2. Base de conhecimento: listagem, criação, edição, desativação e sincronia ChromaDB sem duplicação."""
    student_headers = get_headers(STUDENT_EMAIL, STUDENT_PWD)
    assert client.get("/api/v1/knowledge/", headers=student_headers).status_code == 403

    admin_headers = get_headers(ADMIN_EMAIL, ADMIN_PWD)
    vector_service = VectorStoreService()

    # Listagem inicial
    res_list = client.get("/api/v1/knowledge/", headers=admin_headers)
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 8

    # Criação de novo documento orientativo
    create_payload = {
        "title": "Procedimento Teste Fase 6 — Aproveitamento de Estudos",
        "category": "procedimentos",
        "origin": "Secretaria Acadêmica ASA",
        "version": "1.0-TEST",
        "status": "active",
        "content": (
            "Para solicitar aproveitamento de estudos na FECAP, o estudante deve protocolar "
            "o histórico escolar original e as ementas autenticadas no Portal do Aluno até "
            "o décimo dia útil do semestre letivo."
        ),
        "is_demo": True,
    }
    res_create = client.post("/api/v1/knowledge/", json=create_payload, headers=admin_headers)
    assert res_create.status_code == 201
    doc = res_create.json()
    doc_id = doc["id"]
    assert doc["chunks_count"] >= 1

    # Verifica que os chunks estão no ChromaDB
    chroma_chunks_1 = vector_service.collection.get(where={"document_id": doc_id})
    count_v1 = len(chroma_chunks_1["ids"])
    assert count_v1 == doc["chunks_count"]

    # Edição e atualização de versão (não deve duplicar chunks no ChromaDB)
    update_payload = {
        "version": "1.1-TEST",
        "content": (
            "Versão atualizada: O aproveitamento de estudos exige histórico escolar oficial "
            "e plano de ensino detalhado enviados via requerimento digital no Portal do Aluno."
        ),
    }
    res_update = client.put(f"/api/v1/knowledge/{doc_id}", json=update_payload, headers=admin_headers)
    assert res_update.status_code == 200
    updated_doc = res_update.json()
    assert updated_doc["version"] == "1.1-TEST"

    chroma_chunks_2 = vector_service.collection.get(where={"document_id": doc_id})
    assert len(chroma_chunks_2["ids"]) == updated_doc["chunks_count"]
    assert chroma_chunks_2["metadatas"][0]["version"] == "1.1-TEST"

    # Desativação do documento -> remove vetores do ChromaDB
    res_deactivate = client.patch(
        f"/api/v1/knowledge/{doc_id}/status?new_status=inactive",
        headers=admin_headers,
    )
    assert res_deactivate.status_code == 200
    deactivated_doc = res_deactivate.json()
    assert deactivated_doc["status"] == "inactive"
    assert deactivated_doc["chunks_count"] == 0

    chroma_chunks_after = vector_service.collection.get(where={"document_id": doc_id})
    assert len(chroma_chunks_after["ids"]) == 0


def test_knowledge_file_upload_txt():
    """3. Upload autorizado de arquivo TXT com extração e indexação."""
    admin_headers = get_headers(ADMIN_EMAIL, ADMIN_PWD)
    file_content = (
        "Normativa de Estágio Supervisionado FECAP: O aluno deve enviar o Termo de Compromisso "
        "assinado digitalmente com antecedência mínima de 5 dias úteis antes do início."
    ).encode("utf-8")

    files = {"file": ("normativa_estagio_teste.txt", io.BytesIO(file_content), "text/plain")}
    data = {
        "title": "Normativa Upload TXT Teste",
        "category": "estagios",
        "origin": "Coordenadoria de Estágios",
        "version": "2.0-UPLOAD",
        "status": "inactive",  # inactive para não poluir a base ativa após teste
    }
    res = client.post("/api/v1/knowledge/upload", files=files, data=data, headers=admin_headers)
    assert res.status_code == 201
    uploaded = res.json()
    assert uploaded["title"] == "Normativa Upload TXT Teste"
    assert "Termo de Compromisso" in uploaded["content"]


def test_unanswered_and_rf08_human_validation():
    """4, 5 e 6. Dúvidas sem resposta e fluxo completo de Validação Humana RF08."""
    student_headers = get_headers(STUDENT_EMAIL, STUDENT_PWD)
    admin_headers = get_headers(ADMIN_EMAIL, ADMIN_PWD)

    # Faz uma pergunta fora do escopo para gerar abstenção real (requires_human=True)
    q_res = client.post(
        "/api/v1/agent/query",
        json={"question": "Qual o horário do ônibus espacial para Marte saindo do campus?"},
        headers=student_headers,
    )
    assert q_res.status_code == 200
    q_data = q_res.json()
    msg_id = q_data["id"]
    assert msg_id is not None

    # Lista perguntas sem resposta como admin
    un_res = client.get("/api/v1/agent/unanswered", headers=admin_headers)
    assert un_res.status_code == 200
    unanswered_list = un_res.json()
    assert isinstance(unanswered_list, list)

    # Tentativa de validação RF08 do tipo 'adjust' SEM justificativa -> deve falhar (400)
    bad_val = client.post(
        "/api/v1/agent/validations",
        json={
            "message_id": msg_id,
            "decision": "adjust",
            "justification": "",
            "adjusted_answer": "Orientação revisada pela secretaria.",
        },
        headers=admin_headers,
    )
    assert bad_val.status_code == 400

    # Validação RF08 válida com decisão 'complement', classificação e justificativa
    good_val = client.post(
        "/api/v1/agent/validations",
        json={
            "message_id": msg_id,
            "decision": "complement",
            "classification": "fora_escopo",
            "justification": "Pergunta fora do escopo acadêmico institucional; resposta complementada.",
            "adjusted_answer": "A FECAP não possui transporte espacial. Consulte os canais oficiais da Secretaria.",
            "response_version": "1.0",
        },
        headers=admin_headers,
    )
    assert good_val.status_code == 201
    val_data = good_val.json()
    assert val_data["message_id"] == msg_id
    assert val_data["decision"] == "complement"
    assert val_data["response_version"].endswith("-REV")

    # Lista validações registradas
    list_val = client.get("/api/v1/agent/validations", headers=admin_headers)
    assert list_val.status_code == 200
    assert any(v["id"] == val_data["id"] for v in list_val.json())


def test_handoff_admin_update_and_audit_trail():
    """5 e 7. Atualização administrativa de encaminhamento humano e verificação na auditoria."""
    student_headers = get_headers(STUDENT_EMAIL, STUDENT_PWD)
    admin_headers = get_headers(ADMIN_EMAIL, ADMIN_PWD)

    # Estudante cria handoff
    create_res = client.post(
        "/api/v1/handoff/",
        json={
            "category": "financeiro",
            "priority": "priority",
            "reason": "Dúvida sobre negociação de mensalidade em atraso.",
        },
        headers=student_headers,
    )
    assert create_res.status_code == 201
    protocol = create_res.json()["protocol"]

    # Estudante tenta atualizar status do handoff -> 403 Forbidden
    forbidden_patch = client.patch(
        f"/api/v1/handoff/{protocol}",
        json={"status": "resolved"},
        headers=student_headers,
    )
    assert forbidden_patch.status_code == 403

    # Admin atualiza status, responsável e observações
    patch_res = client.patch(
        f"/api/v1/handoff/{protocol}",
        json={
            "status": "in_progress",
            "attendant": "Setor Financeiro FECAP",
            "summary": "Em análise pelo analista financeiro responsável.",
        },
        headers=admin_headers,
    )
    assert patch_res.status_code == 200
    updated_ticket = patch_res.json()
    assert updated_ticket["status"] == "in_progress"
    assert updated_ticket["attendant"] == "Setor Financeiro FECAP"
    assert "Em análise" in updated_ticket["summary"]

    # Verifica registro na trilha de auditoria filtrando por resource=handoff
    audit_res = client.get("/api/v1/audit/?resource=handoff", headers=admin_headers)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert any(log["action"] == "handoff_updated" and protocol in (log["detail"] or "") for log in logs)


def test_audit_sanitization_prevents_secret_exposure():
    """7. Garante que sanitize_detail mascare senhas, tokens e segredos na auditoria."""
    from app.api.v1.audit import sanitize_detail

    raw = "Tentativa de login com password=minhasenha123 e token: eyJhbGciOiJIUz"
    sanitized = sanitize_detail(raw)
    assert "minhasenha123" not in sanitized
    assert "eyJhbGciOiJIUz" not in sanitized
    assert "[REDACTED]" in sanitized

