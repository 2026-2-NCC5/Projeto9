"""Testes: resposta RAG fundamentada e limitação documentada (Azure bug 2)."""
from unittest.mock import MagicMock, patch

from app.agent.rag_pipeline import RAGPipeline, _build_demo_answer, _extract_procedural_steps
from app.core.config import settings
from app.schemas.schemas import AgentEvidence, AgentQuery

DECL_CHUNK = (
    "TITULO: DECLARACAO DE MATRICULA (DEMONSTRACAO)\n\n"
    "Etapa 1: Acesse o Portal do Aluno (DEMONSTRACAO)\n"
    "Etapa 3: Navegue em: Documentos > Declaracao de Matricula\n"
    "Etapa 5: Clique em \"Emitir Declaracao\"\n"
    "Etapa 6: O documento sera gerado em formato PDF\n"
    "\n1. OUTRO ASSUNTO\nGrade de horarios do semestre\n"
)


def _store(results):
    vs = MagicMock()
    vs.query.return_value = results
    vs.query_similar.return_value = results
    return vs


def test_answer_uses_retrieved_steps_and_cites_document():
    ev = [AgentEvidence(chunk=DECL_CHUNK, document="Declaracao de Matricula - Procedimento", relevance_score=0.7)]
    ans = _build_demo_answer("Como posso solicitar uma declaração de matrícula?", ev)
    steps = _extract_procedural_steps("Como posso solicitar uma declaração de matrícula?", ev)
    assert "Portal do Aluno" in ans
    assert "Recebi sua consulta" not in ans
    assert "(DEMONSTRACAO)" not in ans
    assert "TITULO:" not in ans
    assert "OUTRO ASSUNTO" not in ans
    assert "Grade de horarios" not in ans
    assert "Matrícula" in ans or "matricula" in ans.lower()
    assert steps is not None and any("Documentos > Declaracao de Matricula" in s for s in steps)


def test_out_of_scope_gives_limitation_and_human_handoff():
    pipeline = RAGPipeline(vector_store=_store([]))
    with patch.object(settings, "llm_mode", "demo"):
        resp = pipeline.run(AgentQuery(question="Qual a receita de bolo de cenoura premiada?", student_id="x"))
    assert resp.requires_human is True
    assert resp.next_action == "handoff"
    assert resp.answer


def test_quick_buttons_and_variations_topics():
    """
    Valida que historico escolar, comprovante de matricula, trancamento e prazos de avaliacoes
    usam os chunks como contexto interno (nunca despejando blocos brutos ou misturando assuntos).
    """
    tranc_chunk = (
        "1. REMATRICULA\n1.1 Renovacao da matricula\n"
        "2. TRANCAMENTO DE MATRICULA (DEMONSTRACAO)\n"
        "2.2 Tipos:\n- Trancamento parcial: trancar disciplinas especificas\n"
        "- Trancamento total: trancar o semestre inteiro\n"
        "2.3 Como solicitar:\nEtapa 1: Acesse o Portal do Aluno\n"
        "Etapa 2: Va em Solicitacoes > Trancamento\n"
        "Etapa 3: Selecione o tipo (parcial ou total)\n"
    )
    ev_tranc = [AgentEvidence(chunk=tranc_chunk, document="Procedimentos Administrativos - Guia do Estudante", relevance_score=0.65)]
    for q in ["Como trancar matéria?", "Quero cancelar uma disciplina", "Como faço para trancar o semestre?"]:
        ans = _build_demo_answer(q, ev_tranc)
        steps = _extract_procedural_steps(q, ev_tranc)
        assert "Trancamento" in ans
        assert "parcial" in ans.lower() and "total" in ans.lower()
        assert "1. REMATRICULA" not in ans
        assert "2. TRANCAMENTO" not in ans
        assert steps is not None and len(steps) >= 3

    hist_chunk = (
        "1.1 Declaracao de Matricula\n"
        "1.2 Historico Escolar\n- Relacao de disciplinas cursadas com notas e situacao\n"
        "- Prazo de emissao: ate 3 dias uteis (DEMONSTRACAO)\n"
        "1.3 Atestado de Conclusao de Curso\n"
        "2. COMO SOLICITAR\nEtapa 1: Acesse o Portal do Aluno\n"
        "Etapa 2: Navegue ate a secao Documentos\nEtapa 3: Selecione o tipo de documento desejado\n"
    )
    ev_hist = [AgentEvidence(chunk=hist_chunk, document="Solicitacao de Documentos Academicos", relevance_score=0.68)]
    for q in ["Como emitir histórico escolar oficial?", "Preciso do meu histórico"]:
        ans = _build_demo_answer(q, ev_hist)
        steps = _extract_procedural_steps(q, ev_hist)
        assert "Histórico Escolar" in ans
        assert "3 dias úteis" in ans or "3 dias uteis" in ans
        assert "1.1 Declaracao" not in ans
        assert "1.3 Atestado" not in ans
        assert "2. COMO SOLICITAR" not in ans
        assert steps is not None and len(steps) >= 3

    cal_chunk = "1.3 Prazo: conforme calendario academico\n1.4 Nao ha prazo fixo neste documento — consulte o calendario oficial\n"
    ev_cal = [AgentEvidence(chunk=cal_chunk, document="Procedimentos Administrativos - Guia do Estudante", relevance_score=0.65)]
    for q in ["Quando serão minhas provas?", "Quais os prazos de provas e calendário acadêmico?"]:
        ans = _build_demo_answer(q, ev_cal)
        steps = _extract_procedural_steps(q, ev_cal)
        assert "Calendário Acadêmico" in ans
        assert "1.3 Prazo" not in ans
        assert steps is None
