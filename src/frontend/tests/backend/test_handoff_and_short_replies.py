"""
Testes automatizados para o fluxo de Atendimento Humano Simulado e Respostas Curtas.
Cobre:
  1. Interpretacao de respostas curtas ("sim", "nao", "obrigada", "encerrar") no pipeline RAG.
  2. Ausencia de afirmacoes falsas de validacao institucional pela FECAP.
  3. Identificacao clara do atendente como SIMULADO quando DEMO_MODE (llm_mode="demo") esta ativo.
  4. Vinculacao do protocolo a conversa (conversation_id) e ao assunto (reason/summary) corretos.
  5. Encerramento do protocolo de atendimento humano (status="resolved") pelo estudante e
     restauracao/continuidade da operacao do agente de IA na mesma conversa.
"""
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.agent.rag_pipeline import RAGPipeline
from app.core.config import settings
from app.main import app
from app.schemas.schemas import AgentQuery

client = TestClient(app)

STUDENT_EMAIL = "estudante@demo.fecap.br"
STUDENT_PWD = "demo1234"


def _login_student() -> dict:
    res = client.post(
        "/api/v1/auth/login",
        json={"email": STUDENT_EMAIL, "password": STUDENT_PWD},
    )
    assert res.status_code == 200, f"Falha no login: {res.text}"
    return res.json()


def test_short_replies_in_rag_pipeline():
    """
    1. Testa que respostas curtas ("nao", "sim", "obrigada", "encerrar") sao interpretadas
    corretamente sem consultar vetores aleatorios e sem afirmar validacao na Secretaria Geral.
    """
    pipeline = RAGPipeline()

    # Caso "não" -> encerramento cordial
    res_no = pipeline.run(AgentQuery(question="não", student_id="std_1"))
    assert res_no.next_action == "close"
    assert res_no.requires_human is False
    assert "finalizado" in res_no.answer.lower() or "encerrar" in res_no.answer.lower()
    assert 'solicitação sobre "não"' not in res_no.answer.lower()
    assert "validado diretamente junto à secretaria geral" not in res_no.answer.lower()

    # Caso "sim" -> convite para enviar a proxima duvida
    res_yes = pipeline.run(AgentQuery(question="sim", student_id="std_1"))
    assert res_yes.next_action == "none"
    assert res_yes.requires_human is False
    assert "dúvida" in res_yes.answer.lower() or "procedimento" in res_yes.answer.lower()

    # Caso "obrigada" -> resposta de cortesia
    res_thanks = pipeline.run(AgentQuery(question="obrigada!", student_id="std_1"))
    assert res_thanks.next_action == "none"
    assert "disposição" in res_thanks.answer.lower()

    # Caso "encerrar" -> encerramento imediato
    res_close = pipeline.run(AgentQuery(question="encerrar", student_id="std_1"))
    assert res_close.next_action == "close"
    assert res_close.requires_human is False


def test_handoff_protocol_persistence_subject_binding_and_simulado_label():
    """
    2. Verifica que o protocolo de atendimento humano:
       - fica vinculado a conversa (conversation_id) e ao assunto (reason/summary) corretos;
       - identifica claramente o atendente como SIMULADO quando llm_mode='demo';
       - permite encerrar o atendimento (status='resolved') e continuar usando o agente IA.
    """
    auth = _login_student()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    # Etapa A: Estudante faz uma pergunta ao Agente IA que cria uma conversa persistida
    q_res = client.post(
        "/api/v1/agent/query",
        json={"question": "Como solicitar trancamento de matricula?", "student_id": auth["user"]["id"]},
        headers=headers,
    )
    assert q_res.status_code == 200
    q_data = q_res.json()
    conversation_id = q_data.get("conversation_id")
    assert conversation_id is not None

    # Etapa B: Estudante solicita transferencia para atendimento humano vinculada a conversa e ao assunto
    subject_reason = "Dúvida de Matrícula ou Requerimento — Como solicitar trancamento de matricula?"
    with patch.object(settings, "llm_mode", "demo"):
        h_res = client.post(
            "/api/v1/handoff/",
            json={
                "conversation_id": conversation_id,
                "category": "matricula",
                "priority": "normal",
                "reason": subject_reason,
                "summary": f"Encaminhamento contextual sobre: {subject_reason}",
            },
            headers=headers,
        )
    assert h_res.status_code == 201, h_res.text
    ticket = h_res.json()

    protocol = ticket["protocol"]
    assert protocol.startswith("FECAP-")
    assert ticket["conversation_id"] == conversation_id
    assert ticket["reason"] == subject_reason
    assert "SIMULADO" in ticket["attendant"]

    # Etapa C: Consultar o protocolo persistido no SQLite
    get_res = client.get(f"/api/v1/handoff/{protocol}", headers=headers)
    assert get_res.status_code == 200
    persisted = get_res.json()
    assert persisted["protocol"] == protocol
    assert persisted["conversation_id"] == conversation_id
    assert persisted["reason"] == subject_reason
    assert "SIMULADO" in persisted["attendant"]

    # Etapa D: Estudante responde "não" à oferta de ajuda adicional e encerra o atendimento humano
    close_res = client.post(
        f"/api/v1/handoff/{protocol}/close",
        headers=headers,
    )
    assert close_res.status_code == 200, close_res.text
    resolved_ticket = close_res.json()
    assert resolved_ticket["status"] == "resolved"

    # Etapa E: Garantir que apos encerrar o atendimento humano, o agente de IA volta a responder na mesma conversa
    follow_up_ai = client.post(
        "/api/v1/agent/query",
        json={
            "question": "Como emitir declaracao de matricula no portal?",
            "student_id": auth["user"]["id"],
            "conversation_id": conversation_id,
        },
        headers=headers,
    )
    assert follow_up_ai.status_code == 200
    ai_data = follow_up_ai.json()
    assert ai_data["conversation_id"] == conversation_id
    assert len(ai_data["answer"]) > 20
    assert "validado diretamente junto à secretaria geral" not in ai_data["answer"].lower()
