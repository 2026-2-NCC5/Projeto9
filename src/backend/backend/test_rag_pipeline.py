"""
Testes automatizados da Fase 3 — Agente RAG (Orientacao ao Estudante).
Cobre:
  1. Validacao de pergunta vazia.
  2. Consulta com evidencias e construcao no modo demo.
  3. Presenca de metadados, disclaimer demo e passos.
  4. Abstencao responsavel (score baixo / sem evidencia -> requires_human=True).
  5. Calculo de confianca composta (mediana + bonus).
  6. Modo Gemini simulado (mock com unittest.mock).
  7. Fallback gracioso para modo demo se o Gemini falhar.
  8. Integracao com endpoint POST /api/v1/agent/query (FastAPI TestClient).
  9. Validacao de schema compativel com TypeScript frontend.
  10. Determinismo e isolamento sem chamadas externas a APIs reais.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.schemas import AgentQuery, AgentResponse
from app.agent.rag_pipeline import (
    RAGPipeline,
    _compute_confidence,
    _filter_evidence,
    _build_context_block,
    _build_demo_answer,
)
from app.core.config import settings


@pytest.fixture
def mock_vector_store():
    """Mock do VectorStoreService para controle exato dos resultados."""
    vs = MagicMock()
    return vs


def test_empty_query_validation():
    """1. Teste de validacao de pergunta vazia."""
    pipeline = RAGPipeline()
    query = AgentQuery(question="   ", student_id="student_123")
    res = pipeline.run(query)

    assert isinstance(res, AgentResponse)
    assert res.confidence == 0.0
    assert "valida" in res.answer.lower()
    assert res.requires_human is False


def test_compute_confidence_median_and_coverage():
    """2. Teste do calculo de confianca por mediana + bonus de cobertura."""
    # Lista vazia
    assert _compute_confidence([]) == 0.0

    # Scores com outlier alto (ex: 0.9, 0.4, 0.4) -> mediana 0.4 + bonus 0.03 = 0.43
    scores = [0.90, 0.40, 0.40]
    conf = _compute_confidence(scores)
    assert conf == 0.43

    # Scores uniformes altos
    scores_high = [0.85, 0.82, 0.80]
    conf_high = _compute_confidence(scores_high)
    assert conf_high == 0.85  # 0.82 + 0.03


def test_filter_evidence_threshold():
    """3. Teste de descarte de chunks com score abaixo do limiar configurado."""
    raw = [
        {"text": "Trecho 1", "similarity_score": 0.65, "metadata": {"title": "Doc A"}},
        {"text": "Trecho 2", "similarity_score": 0.20, "metadata": {"title": "Doc B"}},
    ]
    with patch.object(settings, "agent_min_evidence_score", 0.35):
        filtered = _filter_evidence(raw)
        assert len(filtered) == 1
        assert filtered[0].document == "Doc A"
        assert filtered[0].relevance_score == 0.65


def test_rag_pipeline_demo_mode_success(mock_vector_store):
    """4. Pipeline em modo demo: recupera evidencias, gera resposta e disclaimer sem LLM externa."""
    mock_vector_store.query_similar.return_value = [
        {
            "id": "doc1_chunk_0",
            "text": "Para solicitar declaracao de matricula acesse o Portal do Aluno em Solicitacoes.",
            "metadata": {"title": "Guia de Documentos e Certidoes", "document_id": "doc_1"},
            "similarity_score": 0.75,
            "cosine_distance": 0.25,
        },
        {
            "id": "doc1_chunk_1",
            "text": "O prazo padrao para emissao digital e de ate 2 dias uteis.",
            "metadata": {"title": "Guia de Documentos e Certidoes", "document_id": "doc_1"},
            "similarity_score": 0.68,
            "cosine_distance": 0.32,
        },
    ]

    pipeline = RAGPipeline(vector_store=mock_vector_store)
    with patch.object(settings, "llm_mode", "demo"):
        res = pipeline.run(AgentQuery(question="Como emitir declaracao?", student_id="std_1"))

    assert res.requires_human is False
    assert res.confidence is not None and res.confidence >= 0.4
    assert len(res.evidence) == 2
    assert "Guia de Documentos e Certidoes" in res.answer
    assert "conteudo de demonstracao" in res.answer.lower()
    assert res.source == "rag_pipeline"


def test_rag_pipeline_abstention_when_low_confidence(mock_vector_store):
    """5. Abstencao responsavel quando score < agent_confidence_threshold."""
    mock_vector_store.query_similar.return_value = [
        {
            "id": "chunk_x",
            "text": "Informacao pouco relevante",
            "metadata": {"title": "Outro Doc"},
            "similarity_score": 0.36,  # Acima de 0.35 (passa pelo filtro individual), mas confianca < 0.4
            "cosine_distance": 0.64,
        }
    ]

    pipeline = RAGPipeline(vector_store=mock_vector_store)
    with patch.object(settings, "agent_confidence_threshold", 0.40):
        res = pipeline.run(AgentQuery(question="Pergunta obscura nao coberta", student_id="std_1"))

    assert res.requires_human is True
    assert res.next_action == "handoff"
    assert "humano" in res.answer.lower()


def test_rag_pipeline_gemini_mode_mocked(mock_vector_store):
    """6. Pipeline em modo Gemini com chamada mockada para testar o fluxo de sucesso."""
    mock_vector_store.query_similar.return_value = [
        {
            "id": "chunk_1",
            "text": "Acesso a biblioteca fisica das 8h as 21h.",
            "metadata": {"title": "Regulamento da Biblioteca"},
            "similarity_score": 0.80,
            "cosine_distance": 0.20,
        }
    ]

    pipeline = RAGPipeline(vector_store=mock_vector_store)
    with patch.object(settings, "llm_mode", "gemini"), \
         patch.object(settings, "google_api_key", "mock_key_123"), \
         patch("app.agent.rag_pipeline._call_gemini", return_value="O horario da biblioteca e das 8h as 21h."):
        
        res = pipeline.run(AgentQuery(question="Qual horario da biblioteca?", student_id="std_1"))

    assert res.requires_human is False
    assert "8h as 21h" in res.answer
    assert any("Gemini" in s for s in (res.steps or []))


def test_rag_pipeline_gemini_error_fallback(mock_vector_store):
    """7. Fallback elegante para o modo demo caso o provedor Gemini lance erro."""
    mock_vector_store.query_similar.return_value = [
        {
            "id": "chunk_1",
            "text": "Informacoes de estagio curricular e convenios.",
            "metadata": {"title": "Manual de Estagios"},
            "similarity_score": 0.70,
            "cosine_distance": 0.30,
        }
    ]

    pipeline = RAGPipeline(vector_store=mock_vector_store)
    with patch.object(settings, "llm_mode", "gemini"), \
         patch.object(settings, "google_api_key", "mock_key_123"), \
         patch("app.agent.rag_pipeline._call_gemini", side_effect=RuntimeError("API quota exceeded")):
        
        res = pipeline.run(AgentQuery(question="Como faco estagio?", student_id="std_1"))

    assert res.requires_human is False
    assert "Manual de Estagios" in res.answer
    assert any("fallback para demo" in s for s in (res.steps or []))


def test_api_endpoint_post_agent_query():
    """8. Teste de integracao FastAPI: POST /api/v1/agent/query com cliente HTTP."""
    client = TestClient(app)

    payload = {
        "question": "Como solicitar declaracao de matricula?",
        "student_id": "student_demo_01"
    }

    # Executa a query usando a base ChromaDB persistida na Fase 2
    response = client.post("/api/v1/agent/query", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "answer" in data
    assert "requires_human" in data
    assert "evidence" in data
    assert "confidence" in data
    assert isinstance(data["evidence"], list)


def test_api_agent_status_endpoint():
    """9. Teste do status endpoint GET /api/v1/agent/."""
    client = TestClient(app)
    response = client.get("/api/v1/agent/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_schema_frontend_compatibility():
    """10. Garante que os campos do AgentResponse batem com o tipo AgentResponse do frontend TypeScript."""
    evidence = [
        {"chunk": "texto 1", "document": "Doc 1", "relevance_score": 0.7}
    ]
    resp = AgentResponse(
        id="uuid-test",
        answer="Resposta de teste",
        steps=["passo 1"],
        next_action="none",
        source="rag_pipeline",
        version="1.0.0",
        updated_at="2026-10-31T20:00:00Z",
        evidence=evidence,
        confidence=0.85,
        requires_human=False,
    )
    dumped = resp.model_dump()
    expected_keys = {
        "id", "answer", "steps", "next_action", "source",
        "version", "updated_at", "evidence", "confidence", "requires_human"
    }
    assert expected_keys.issubset(dumped.keys())


def test_steps_no_duplicate_numbering_prefixes(mock_vector_store):
    """11. Garante que os passos gerados nao possuem prefixos numericos ('1.', '2.', 'Etapa X'), evitando duplicidade no StepsCard."""
    mock_vector_store.query_similar.return_value = [
        {
            "id": "doc_proc_0",
            "text": "2. TRANCAMENTO DE MATRICULA. Trancamento parcial de disciplina.",
            "metadata": {"title": "Procedimentos Administrativos - Guia do Estudante", "document_id": "doc_proc"},
            "similarity_score": 0.85,
            "cosine_distance": 0.15,
        }
    ]

    pipeline = RAGPipeline(vector_store=mock_vector_store)
    with patch.object(settings, "llm_mode", "demo"):
        res = pipeline.run(AgentQuery(question="Como trancar matéria?", student_id="std_1"))

    assert res.steps is not None
    assert len(res.steps) >= 3
    for s in res.steps:
        # Nenhum passo deve comecar com digito seguido de ponto/traco ou Etapa/Passo
        import re
        assert not re.match(r"^\s*(?:\d+[\.\-\)]|(?:Etapa|Passo)\s*\d+)", s, re.I), f"Passo contem prefixo numerico duplicado: {s}"


def test_exam_calendar_abstention_and_temporal_clarification(mock_vector_store):
    """12. Garante que perguntas de provas/calendario nao inventam datas e esclarecem que o calendario homologado deve ser consultado."""
    mock_vector_store.query_similar.return_value = [
        {
            "id": "faq_chunk_0",
            "text": "1.4 Nao ha prazo fixo neste documento - consultar calendario academico vigente. Data de Publicacao: 2024-01-01.",
            "metadata": {"title": "Perguntas Frequentes - FAQ do Estudante", "document_id": "doc_faq"},
            "similarity_score": 0.70,
            "cosine_distance": 0.30,
        }
    ]

    pipeline = RAGPipeline(vector_store=mock_vector_store)
    with patch.object(settings, "llm_mode", "demo"):
        res = pipeline.run(AgentQuery(question="Quais os prazos de provas e calendário acadêmico?", student_id="std_1"))

    assert res.requires_human is False
    # Nao deve afirmar que 2026/1 e o semestre corrente em novembro de 2026
    assert "2026/1" not in res.answer
    # Deve explicitar que as datas exatas nao estao disponiveis na base verificada
    assert "não estão disponíveis na base de conhecimento verificada" in res.answer.lower() or "nao estao disponiveis na base de conhecimento verificada" in res.answer.lower()
    # Deve orientar a consulta ao calendario oficial homologado
    assert "calendário acadêmico" in res.answer.lower() or "calendario academico" in res.answer.lower()
    # Deve conter aviso de demonstracao
    assert "conteudo de demonstracao" in res.answer.lower() or "demonstração" in res.answer.lower()


def test_outdated_document_handling(mock_vector_store):
    """13. Garante que documentos com data de 2024 sao tratados como demonstracao e nao geram falsos prazos vigentes."""
    mock_vector_store.query_similar.return_value = [
        {
            "id": "old_doc_0",
            "text": "Calendario de avaliacoes e provas regimentais. Versao 1.0-DEMO Data de Publicacao: 2024-01-01. Prazos sao indicativos.",
            "metadata": {"title": "Procedimentos Administrativos - Guia do Estudante", "document_id": "doc_old"},
            "similarity_score": 0.75,
            "cosine_distance": 0.25,
        }
    ]

    pipeline = RAGPipeline(vector_store=mock_vector_store)
    with patch.object(settings, "llm_mode", "demo"):
        res = pipeline.run(AgentQuery(question="O calendário de 2024 ainda vale para as provas?", student_id="std_1"))

    # Nao deve assumir validade de normas de 2024 para o periodo corrente
    assert "2024" in res.answer or "calendario" in res.answer.lower() or "não estão disponíveis" in res.answer.lower()
    assert "não coincide automaticamente com o calendário civil" in res.answer.lower() or "não estão disponíveis" in res.answer.lower()

