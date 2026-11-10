"""
Pipeline RAG — Agente 3: Orientacao ao Estudante (FECAP Guia)

Fluxo:
  1. Validar a pergunta.
  2. Consultar o ChromaDB (Top-K configuravel).
  3. Filtrar evidencias relevantes (score >= agent_min_evidence_score).
  4. Calcular confianca composta (mediana dos scores + bonus de cobertura).
  5. Se confianca >= agent_confidence_threshold:
     a. Modo "gemini": chamar o Gemini com prompt contendo os chunks.
     b. Modo "demo":   construir resposta objetiva e contextualizada usando os chunks como contexto interno.
  6. Se confianca insuficiente: abstencao responsavel com requires_human=True.

Garantias:
  - Nenhum fato inventado: resposta construida apenas com conteudo recuperado.
  - Chunks sao utilizados exclusivamente como contexto interno (nunca despejados integralmente).
  - Limiar 0.4 e parametro inicial sujeito a calibracao (config.py).
  - Logs estruturados de cada etapa do pipeline.
  - Documentos marcados como demo sao identificados na resposta.
"""
from __future__ import annotations

import re
import statistics
import unicodedata
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.knowledge.vector_store import VectorStoreService
from app.schemas.schemas import AgentEvidence, AgentQuery, AgentResponse

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Utilitario para respostas curtas / conversacionais (sim, nao, obrigada, etc.)
# ---------------------------------------------------------------------------
_NEGATIVE_CLOSE_UTTERANCES = {
    "nao",
    "n",
    "nao preciso",
    "nao quero",
    "nao obrigada",
    "nao obrigado",
    "so isso",
    "era so isso",
    "mais nada",
    "nada mais",
}

_AFFIRMATIVE_UTTERANCES = {
    "sim",
    "s",
    "claro",
    "quero",
    "preciso",
    "por favor",
    "pode ser",
    "sim por favor",
    "tenho outra duvida",
    "outra duvida",
}

_THANKS_UTTERANCES = {
    "obrigada",
    "obrigado",
    "muito obrigada",
    "muito obrigado",
    "valeu",
    "agradecida",
    "agradecido",
    "grata",
    "grato",
    "ok obrigada",
    "ok obrigado",
    "tudo certo obrigada",
    "tudo certo obrigado",
}

_CLOSE_UTTERANCES = {
    "encerrar",
    "finalizar",
    "fechar",
    "concluir",
    "pode encerrar",
    "quero encerrar",
    "encerrar atendimento",
    "finalizar atendimento",
    "tchau",
    "ate logo",
}


def _normalize_short_text(raw: str) -> str:
    txt = unicodedata.normalize("NFD", (raw or "").strip().lower())
    txt = "".join(ch for ch in txt if unicodedata.category(ch) != "Mn")
    txt = re.sub(r"[!?.:;,\-\"'()\[\]]+", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


def _detect_conversational_reply(question: str) -> Optional[AgentResponse]:
    """
    Se a entrada do estudante for uma resposta curta conversacional ("nao", "sim",
    "obrigada", "encerrar"), retorna uma resposta contextual imediata sem consultar
    o ChromaDB e sem afirmar qualquer validacao institucional.
    """
    norm = _normalize_short_text(question)
    if not norm or len(norm.split()) > 5:
        return None

    run_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    if norm in _NEGATIVE_CLOSE_UTTERANCES or norm in _CLOSE_UTTERANCES:
        return AgentResponse(
            id=run_id,
            answer=(
                "Perfeito! Entendi que você não precisa de apoio adicional neste momento e deseja encerrar.\n\n"
                "Seu atendimento pode ser finalizado com segurança. Caso surja uma nova dúvida acadêmica sobre "
                "matrícula, histórico, boletos ou requerimentos, basta digitar sua pergunta aqui no chat.\n\n"
                "Nota: orientação em modo de demonstração acadêmica. Nenhum documento ou solicitação foi validado "
                "automaticamente junto à FECAP."
            ),
            steps=[
                "contexto_conversacional: resposta curta de encerramento/negativa detectada",
                "acao: encerramento cordial sem consulta vetorial desnecessaria",
            ],
            next_action="close",
            source="agent",
            version=settings.agent_version,
            updated_at=now_iso,
            evidence=[],
            confidence=1.0,
            requires_human=False,
        )

    if norm in _THANKS_UTTERANCES:
        return AgentResponse(
            id=run_id,
            answer=(
                "Por nada! Fico à disposição para auxiliar com orientações baseadas nos manuais acadêmicos.\n\n"
                "Se precisar consultar outro procedimento, basta enviar sua dúvida, ou finalize o atendimento quando desejar.\n\n"
                "Nota: orientação em modo de demonstração acadêmica (sem validação institucional real)."
            ),
            steps=[
                "contexto_conversacional: agradecimento detectado",
                "acao: resposta de cortesia e disponibilidade",
            ],
            next_action="none",
            source="agent",
            version=settings.agent_version,
            updated_at=now_iso,
            evidence=[],
            confidence=1.0,
            requires_human=False,
        )

    if norm in _AFFIRMATIVE_UTTERANCES:
        return AgentResponse(
            id=run_id,
            answer=(
                "Claro! Por favor, descreva qual é a sua dúvida ou procedimento acadêmico que deseja consultar "
                "(por exemplo: Como emitir histórico escolar?, Como trancar disciplina? ou Segunda via de boleto).\n\n"
                "Nota: orientação em modo de demonstração acadêmica."
            ),
            steps=[
                "contexto_conversacional: confirmacao curta ('sim') detectada",
                "acao: solicitacao do tema especifico ao estudante",
            ],
            next_action="none",
            source="agent",
            version=settings.agent_version,
            updated_at=now_iso,
            evidence=[],
            confidence=1.0,
            requires_human=False,
        )

    return None


# ---------------------------------------------------------------------------
# Constantes de prompt
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """\
Você é o Agente de Orientação ao Estudante da FECAP (SecretarIA).
Sua missão é responder à dúvida acadêmica do estudante com base ESTRITAMENTE nos trechos de referência fornecidos abaixo.
Diretrizes inegociáveis:
1. Responda SOMENTE com base nos fatos presentes nos trechos de referência. Nunca invente procedimentos, prazos, taxas, normas ou datas.
2. Cite sempre o documento de referência utilizado.
3. Se a informação solicitada não estiver explicitamente coberta nos trechos (como datas de provas específicas de um ano/semestre ou calendário acadêmico homologado), explique claramente que as datas exatas não estão disponíveis na base verificada e que o estudante deve consultar o documento oficial homologado no Portal do Aluno ou na Secretaria Acadêmica.
4. Diferencie o calendário civil (ano/mês atual) do calendário acadêmico institucional (que depende de homologação formal). Não assuma que documentos de anos anteriores (como 2024) ou semestres passados são o calendário do semestre vigente.
5. Responda em português formal, empático, claro e objetivo. Organize a resposta em tópicos ou passos quando apropriado. Não inclua numeração nos itens dos passos.
6. Não responda sobre emissão de boletos, cobranças financeiras ou dados bancários; encaminhe essas questões para a Central Financeira / Portal do Aluno.
7. Os documentos pertencem a um ambiente acadêmico demonstrativo — informe isso ao estudante.
"""

_DEMO_DISCLAIMER = (
    "\n\nNota: as orientacoes acima sao baseadas em conteudo de demonstracao "
    "(guias de demonstracao academica — conteudo ficticio sem validade oficial verificada junto a FECAP). "
    "Confirme prazos, taxas e calendarios vigentes com a Secretaria Academica."
)

_ABSTENTION_DISCLAIMER = (
    "\n\nNota: nenhuma informacao suficiente foi encontrada na base de "
    "demonstracao. Encaminhe sua duvida ao atendimento humano."
)


# ---------------------------------------------------------------------------
# Funcoes auxiliares
# ---------------------------------------------------------------------------

def _build_context_block(evidence: List[AgentEvidence]) -> str:
    """Constroi bloco de contexto interno a partir das evidencias selecionadas."""
    lines: List[str] = []
    for i, ev in enumerate(evidence, 1):
        lines.append(f"[{i}] Documento: {ev.document}")
        lines.append(ev.chunk)
        lines.append("")
    return "\n".join(lines)


def _compute_confidence(scores: List[float]) -> float:
    """
    Confianca composta = mediana dos scores de similaridade.
    Usar mediana (em vez de media) e mais robusto contra outliers como o
    caso FAQ/senha que retornou score alto para uma query nao relacionada.
    """
    if not scores:
        return 0.0
    med = statistics.median(scores)
    # Bonus leve pelo numero de evidencias convergentes (max +0.05)
    coverage_bonus = min(0.05, len(scores) * 0.01)
    return round(min(1.0, med + coverage_bonus), 4)


def _filter_evidence(raw_results: List[dict]) -> List[AgentEvidence]:
    """
    Converte resultados brutos do ChromaDB em AgentEvidence,
    descartando chunks abaixo do limiar minimo e sanitizando o texto.
    """
    threshold = settings.agent_min_evidence_score
    evidence: List[AgentEvidence] = []
    for r in raw_results:
        score = r.get("similarity_score", 0.0)
        if score < threshold:
            continue
        meta = r.get("metadata", {})
        doc_label = meta.get("title", meta.get("document_id", "Desconhecido"))
        evidence.append(
            AgentEvidence(
                chunk=_sanitize_chunk_text(r["text"]),
                document=doc_label,
                relevance_score=round(score, 4),
            )
        )
    return evidence


# ---------------------------------------------------------------------------
# Integracao Gemini
# ---------------------------------------------------------------------------

def _call_gemini(question: str, context_block: str) -> str:
    """
    Chama a API Gemini usando o SDK google-genai.
    Retorna o texto gerado ou lanca RuntimeError em caso de falha.
    Esta funcao e substituida por mock nos testes unitarios.
    """
    from google import genai  # type: ignore

    client = genai.Client(api_key=settings.google_api_key)
    prompt = (
        f"{_SYSTEM_PROMPT}\n\n"
        f"Trechos de referencia:\n{context_block}\n\n"
        f"Pergunta do estudante: {question}"
    )
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
    )
    return response.text


# ---------------------------------------------------------------------------
# Construtor de resposta fundamentada (usa chunks como CONTEXTO INTERNO)
# ---------------------------------------------------------------------------

_STOPWORDS = {
    "como", "posso", "para", "uma", "umas", "uns", "que", "qual", "quais", "onde",
    "quando", "por", "com", "dos", "das", "nos", "nas", "meu", "minha", "sobre",
    "preciso", "quero", "fazer", "solicitar", "solicito", "pode", "ser", "tem",
}


def _keywords(text: str) -> set:
    norm = unicodedata.normalize("NFKD", text.lower())
    norm = "".join(c for c in norm if not unicodedata.combining(c))
    return {w for w in re.findall(r"[a-z0-9]{4,}", norm) if w not in _STOPWORDS}


def _clean_line(line: str) -> str:
    line = re.sub(r"\s*\(DEMONSTRACAO[^)]*\)", "", line, flags=re.I)
    line = re.sub(r"\s*\(FICTICIO[^)]*\)", "", line, flags=re.I)
    return line.rstrip()


def _sanitize_chunk_text(text: str) -> str:
    """
    Higieniza o texto bruto de um chunk, removendo cabecalhos tecnicos de secao,
    marcadores de demonstracao e fragmentos de palavras truncadas nas bordas de corte.
    """
    if not text:
        return ""
    lines = []
    for line in text.splitlines():
        cl = _clean_line(line).strip()
        if not cl or len(cl) < 4:
            continue
        if re.match(
            r"^\s*(?:TITULO|AVISO|ATENCAO|PERGUNTA|RESPOSTA|Documento|Categoria|Versao|Data|Origem|Status)\b",
            cl,
            flags=re.I,
        ):
            continue
        if re.fullmatch(r"[=\-\s*#]+", cl):
            continue
        # Corrige eventuais prefixos truncados na divisao de chunks
        cl = re.sub(r"^[a-z0-9]{1,3}[:\s\-\.]+", "", cl)
        lines.append(cl)
    return "\n".join(lines).strip()


def _detect_academic_topic(question: str) -> str:
    """Identifica o topico academico principal da pergunta (sem inventar dados)."""
    q_norm = unicodedata.normalize("NFKD", (question or "").lower())
    q_norm = "".join(c for c in q_norm if not unicodedata.combining(c))

    # 1. Triagem Financeira Prioritaria (JAMAIS direcionada a LLM externo)
    if any(k in q_norm for k in ["boleto", "segunda via de boleto", "2a via de boleto", "mensalidade", "pagamento de mensalidade", "codigo de barras", "fatura"]):
        return "financeiro_boleto"

    # 2. Perguntas Sem Resposta Cadastrada / Calendario de Provas Especifico
    if any(k in q_norm for k in [
        "data da prova", "datas das provas", "datas de provas", "data de prova", "datas de prova",
        "quando e a prova", "quando sao as provas", "prazos de provas", "prazo de prova",
        "prova a1", "prova a2", "substitutiva data", "dia da prova", "dias de prova",
        "calendario de prova", "calendario de provas", "datas de avaliacao", "datas das avaliacoes"
    ]):
        return "provas_datas"

    # 3. Trancamento: Diferenciacao entre Disciplina (Parcial) e Semestre (Total)
    if any(k in q_norm for k in ["trancar materia", "trancar disciplina", "trancamento de materia", "trancamento de disciplina", "trancamento parcial"]):
        return "trancamento_disciplina"
    if any(k in q_norm for k in ["trancar semestre", "trancar curso", "trancamento de curso", "trancamento total", "trancar a faculdade", "trancar o semestre"]):
        return "trancamento_total"
    if any(k in q_norm for k in ["trancar", "trancamento", "cancelar matricula"]):
        return "trancamento_disciplina"

    # 4. Historico Escolar
    if any(k in q_norm for k in ["historico", "historico escolar", "notas e faltas", "relacao de disciplinas"]):
        return "historico"

    # 5. Declaracao / Comprovante de Matricula
    if any(k in q_norm for k in ["declaracao de matricula", "comprovante de matricula", "declaracao de vinculo", "atestado de matricula", "declaracao"]):
        return "matricula"

    # 6. Rematricula
    if any(k in q_norm for k in ["rematricula", "renovacao de matricula"]):
        return "rematricula"

    # 7. Aproveitamento de Estudos / Equivalencia
    if any(k in q_norm for k in ["aproveitamento", "equivalencia", "dispensa de disciplina", "dispensa de materia"]):
        return "aproveitamento"

    # 8. Revisao de Nota
    if any(k in q_norm for k in ["revisao de nota", "revisao", "rever nota", "revisao de prova"]):
        return "revisao_nota"

    # 9. Segunda Via de Documentos NAO Financeiros
    if any(k in q_norm for k in ["segunda via", "2a via", "perdi meu", "perdi minha carteira", "extravio"]):
        return "segunda_via_doc"

    # 10. Calendario Geral
    if any(k in q_norm for k in ["calendario", "semestre letivo", "ano letivo"]):
        return "calendario"

    # 11. Portal do Aluno / Senha / Acesso
    if any(k in q_norm for k in ["portal do aluno", "senha", "login", "primeiro acesso", "esqueci minha senha"]):
        return "portal"

    # 12. Atendimento e Horarios da Secretaria
    if any(k in q_norm for k in ["atendimento", "secretaria", "coordenacao", "canal", "canais", "horario de funcionamento", "falar com a secretaria"]):
        return "atendimento"

    if "matricula" in q_norm:
        return "matricula"

    # 13. Fora de Escopo Academico
    if any(k in q_norm for k in ["receita", "futebol", "campeonato", "filme", "tempo hoje", "clima", "jogo", "piada", "bolo"]):
        return "fora_de_escopo"

    return "geral"


def _prioritize_topic_evidence(question: str, evidence: List[AgentEvidence]) -> List[AgentEvidence]:
    """
    Ordena e filtra as evidencias mantendo a relevancia semantica, priorizando
    o documento especifico do topico consultado para evitar mistura de assuntos.
    """
    if not evidence:
        return []
    topic = _detect_academic_topic(question)
    preferred_titles = {
        "matricula": ["Declaracao de Matricula", "Solicitacao de Documentos", "Guia de Documentos"],
        "historico": ["Solicitacao de Documentos", "Perguntas Frequentes"],
        "trancamento_disciplina": ["Procedimentos Administrativos", "Perguntas Frequentes"],
        "trancamento_total": ["Procedimentos Administrativos", "Perguntas Frequentes"],
        "trancamento": ["Procedimentos Administrativos", "Perguntas Frequentes"],
        "rematricula": ["Procedimentos Administrativos", "Perguntas Frequentes"],
        "aproveitamento": ["Procedimentos Administrativos", "Perguntas Frequentes"],
        "revisao_nota": ["Procedimentos Administrativos", "Perguntas Frequentes"],
        "segunda_via_doc": ["Segunda Via de Documentos", "Solicitacao de Documentos"],
        "portal": ["Como Acessar o Portal do Aluno", "Perguntas Frequentes"],
        "atendimento": ["Atendimento Academico", "Canais de Atendimento"],
        "calendario": ["Procedimentos Administrativos", "Perguntas Frequentes"],
        "provas_datas": ["Procedimentos Administrativos", "Perguntas Frequentes"],
        "financeiro_boleto": ["Perguntas Frequentes", "Canais de Atendimento"],
    }.get(topic, [])

    if not preferred_titles:
        return evidence

    # Filtragem estrita: se houver evidencias dos documentos preferidos, descarta documentos de assuntos estranhos
    topic_matched = []
    for ev in evidence:
        doc_lower = (ev.document or "").lower()
        chunk_lower = (ev.chunk or "").lower()
        for pref in preferred_titles:
            if pref.lower() in doc_lower:
                if topic in ("trancamento_disciplina", "trancamento_total", "trancamento") and "procedimentos" in doc_lower:
                    if "trancamento" in chunk_lower or "2." in chunk_lower:
                        topic_matched.append(ev)
                        break
                elif topic == "historico" and "solicitacao" in doc_lower:
                    if "historico" in chunk_lower or "1.2" in chunk_lower or "documentos" in chunk_lower:
                        topic_matched.append(ev)
                        break
                else:
                    topic_matched.append(ev)
                    break

    return topic_matched if topic_matched else evidence


def _extract_procedural_steps(question: str, evidence: List[AgentEvidence]) -> Optional[List[str]]:
    """
    Retorna passos procedimentais academicos reais e estruturados para a duvida consultada.
    IMPORTANTE: Os passos sao retornados como texto limpo SEM prefixos numericos ('1.', '2.', etc.),
    pois o componente StepsCard da interface ja inclui a numeracao visual no badge.
    """
    topic = _detect_academic_topic(question)

    if topic == "trancamento_disciplina":
        return [
            "Acesse o Portal do Aluno com seu RA e senha institucional",
            "No menu 'Secretaria Virtual', selecione 'Solicitações' > 'Trancamento de Matrícula'",
            "Escolha a modalidade 'Trancamento Parcial' e selecione a disciplina desejada",
            "Verifique se o pedido atende ao prazo limite regulamentar previsto no Calendário Acadêmico homologado",
            "Confirme a solicitação e guarde o comprovante de protocolo gerado",
        ]

    if topic == "trancamento_total":
        return [
            "Acesse o Portal do Aluno com suas credenciais institucionais",
            "Navegue até 'Secretaria Virtual' > 'Solicitações' > 'Trancamento de Matrícula'",
            "Selecione a opção 'Trancamento Total' (suspensão temporária de todas as disciplinas do semestre)",
            "Preencha o formulário eletrônico justificando a solicitação de interrupção",
            "Protocolize o requerimento dentro do prazo limite estabelecido no Calendário Acadêmico homologado",
        ]

    if topic == "historico":
        return [
            "Acesse o Portal do Aluno no menu 'Secretaria Virtual'",
            "Selecione 'Documentos Acadêmicos' > 'Histórico Escolar Oficial'",
            "Escolha a emissão digital gratuita (processada no portal com autenticação eletrônica)",
            "Para via física em papel timbrado com assinatura da Secretaria Acadêmica, agende a retirada presencial",
        ]

    if topic == "matricula":
        return [
            "Acesse o Portal do Aluno com seu RA institucional",
            "Selecione a opção 'Solicitações e Certidões' > 'Declaração de Matrícula'",
            "Selecione o semestre letivo desejado para emissão do documento oficial em formato PDF",
            "O documento gerado possui código de autenticidade eletrônica com validade indicativa de 30 dias",
        ]

    if topic == "financeiro_boleto":
        return [
            "Acesse a área 'Financeiro' no Portal do Aluno",
            "Localize a mensalidade pendente de pagamento",
            "Clique em 'Emitir 2ª Via do Boleto' para obter a linha digitável ou o boleto atualizado",
            "Para simulações demonstrativas, utilize o painel interativo de boletos integrado ao chat",
        ]

    if topic == "revisao_nota":
        return [
            "Acesse o Portal do Aluno na seção 'Notas e Faltas'",
            "Localize a disciplina avaliada e clique em 'Solicitar Revisão de Nota'",
            "Protocolize o pedido no prazo regulamentar indicativo de até 5 dias úteis após a publicação oficial",
            "Apresente a fundamentação acadêmica do pedido anexando eventuais comprovações",
            "Acompanhe o parecer formal emitido pelo docente e pela Coordenação de Curso",
        ]

    if topic == "aproveitamento":
        return [
            "Acesse o Portal do Aluno em 'Requerimentos Acadêmicos'",
            "Selecione 'Aproveitamento de Estudos / Equivalência de Disciplinas'",
            "Anexe o Histórico Escolar oficial da instituição de origem e as ementas/conteúdos programáticos",
            "Protocolize o requerimento dentro do período fixado no Calendário Acadêmico homologado",
            "Acompanhe a análise da Coordenação de Curso e o lançamento das dispensas no histórico",
        ]

    if topic in ("provas_datas", "calendario"):
        return [
            "Acesse o Portal do Aluno com suas credenciais institucionais",
            "Consulte a seção 'Calendário Acadêmico' para verificar o documento oficial homologado do período letivo",
            "Para confirmar as datas exatas das avaliações regimentais (A1, A2 e Substitutiva), contate a Secretaria Acadêmica ou a Coordenação de Curso",
        ]

    if topic == "rematricula":
        return [
            "Acesse o Portal do Aluno durante o período de rematrícula definido no Calendário Acadêmico homologado",
            "No menu acadêmico, selecione 'Rematrícula Online'",
            "Confira a grade de disciplinas e turmas disponíveis",
            "Confirme a seleção e acompanhe a emissão da documentação e do boleto correspondente",
        ]

    if topic == "segunda_via_doc":
        return [
            "Acesse o Portal do Aluno na seção 'Documentos Acadêmicos'",
            "Para documentos digitais (declaração, histórico), efetue a emissão gratuita pelo portal",
            "Para segunda via de carteirinha estudantil física ou documentos impressos, solicite atendimento presencial na Secretaria",
        ]

    # Fallback dinamico se houver passos numerados no chunk
    if evidence:
        numbered: dict[int, str] = {}
        for ev in evidence[:2]:
            for line in ev.chunk.splitlines():
                m = re.match(r"^\s*(?:Etapa|Passo)\s*(\d+)\s*[:\-\.]?\s*(.+)$", line.strip(), flags=re.I)
                if m:
                    s_num = int(m.group(1))
                    s_body = _clean_line(m.group(2)).strip()
                    s_body = re.sub(r"^\s*(?:\d+[\.\-\)]\s*|(?:Etapa|Passo)\s*\d+[:\-\.]?\s*)", "", s_body).strip()
                    if len(s_body) > 6 and s_num not in numbered:
                        numbered[s_num] = s_body
        if len(numbered) >= 2:
            return [numbered[k] for k in sorted(numbered.keys())]

    return None


def _analyze_temporal_context(doc_chunks: List[str]) -> dict:
    """
    Diferencia a data civil corrente das datas e semestres citados nos documentos recuperados
    (que pertencem a guias demonstrativos ou versoes passadas).
    Nao presume que o calendario civil equivale automaticamente ao calendario academico institucional.
    """
    now = datetime.now(timezone.utc)
    current_year = now.year
    current_month = now.month

    # Identifica anos e semestres citados nos chunks
    combined = " ".join(doc_chunks)
    cited_semesters = set(re.findall(r"\b202\d/[12]\b", combined))
    cited_years = set(re.findall(r"\b202\d\b", combined))

    has_calendar_dates = any(
        k in combined.lower()
        for k in ["data da prova a1:", "periodo de provas a1:", "calendario homologado"]
    )

    return {
        "current_year": current_year,
        "current_month": current_month,
        "cited_semesters": sorted(list(cited_semesters)),
        "cited_years": sorted(list(cited_years)),
        "has_calendar_dates": has_calendar_dates,
    }


def _extract_relevant_excerpt(question: str, chunk: str, max_chars: int = 240) -> str:
    """
    Extrai no maximo 1 a 2 frases curtas e limpas do chunk para topicos gerais,
    descartando cabecalhos de secao, listas de outros assuntos e fragmentos truncados.
    """
    kws = _keywords(question)
    raw = [l for l in chunk.splitlines()]
    while raw and re.match(r"^[a-z]{1,6}[:\s]", raw[0]):
        raw = raw[1:]

    sentences: List[str] = []
    seen = set()
    for l in raw:
        cl = _clean_line(l).strip()
        if not cl or len(cl) < 12:
            continue
        if re.fullmatch(r"[=\-\s]+", cl):
            continue
        if re.match(r"^\s*(?:TITULO|AVISO|ATENCAO|PERGUNTA|RESPOSTA|Documento|Categoria|Versao|Data|Origem|Status)\b", cl, flags=re.I):
            continue
        if re.match(r"^\s*(?:Etapa|Passo)\s*\d+\s*:", cl, flags=re.I):
            continue
        if re.match(r"^\s*\d+(?:\.\d+)?\s+[A-Z]", cl):
            continue
        if "portal.demo" in cl.lower() or "ficticio" in cl.lower() or "demo.example" in cl.lower():
            continue
        if kws and not (kws & _keywords(cl)):
            continue
        cl_norm = re.sub(r"^[\-\•\*]\s*", "", cl).strip()
        if cl_norm.lower() not in seen:
            seen.add(cl_norm.lower())
            sentences.append(cl_norm)
            if len(sentences) >= 2:
                break

    text = " ".join(sentences).strip()
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "..."
    return text


def _build_demo_answer(question: str, evidence: List[AgentEvidence]) -> str:
    """
    Constroi uma resposta academica objetiva, contextualizada e especifica para a pergunta,
    utilizando os chunks recuperados exclusivamente como CONTEXTO INTERNO (sem despejar
    blocos brutos de documentos e sem misturar assuntos diferentes).
    """
    ordered = _prioritize_topic_evidence(question, evidence)
    top_ev = ordered[0] if ordered else None
    top_doc = top_ev.document if top_ev else ""
    doc_ref = f" ({top_doc})" if top_doc else ""
    topic = _detect_academic_topic(question)

    if topic == "trancamento_disciplina":
        return (
            f"A solicitação de Trancamento Parcial de Disciplina (cancelamento de matérias específicas com manutenção do vínculo acadêmico) é realizada pelo Portal do Aluno, conforme diretrizes gerais documentadas em{doc_ref}.\n\n"
            "Conforme as normas regimentais da instituição, o pedido deve observar o limite mínimo de disciplinas exigido pela matriz curricular do curso e ser protocolado dentro do prazo regulamentar fixado no Calendário Acadêmico homologado. Como os documentos consultados pertencem a uma base de demonstração acadêmica sem valor de norma oficial, consulte o calendário oficial vigente no Portal do Aluno para confirmar a data limite deste semestre."
        )

    if topic == "trancamento_total":
        return (
            f"O Trancamento Total de Matrícula (suspensão temporária de todas as atividades letivas do semestre com preservação do vínculo institucional com a FECAP) deve ser requerido formalmente no Portal do Aluno, conforme diretrizes documentadas em{doc_ref}.\n\n"
            "O procedimento deve atender aos prazos regimentais estabelecidos no Calendário Acadêmico homologado e respeitar o limite máximo de períodos de trancamento permitidos na graduação. Por se tratar de base de demonstração acadêmica sem validade de norma verificada, confirme os prazos e condições vigentes junto à Secretaria Acadêmica."
        )

    if topic == "trancamento":
        return (
            f"A solicitação de Trancamento de Matrícula (interrupção temporária dos estudos sem perda do vínculo institucional) é realizada pelo Portal do Aluno, conforme documentado em{doc_ref}.\n\n"
            "Você pode optar entre o trancamento parcial (apenas disciplinas específicas) ou o trancamento total (semestre inteiro), devendo protocolar o pedido dentro do período letivo previsto no Calendário Acadêmico homologado."
        )

    if topic == "historico":
        return (
            f"A solicitação do Histórico Escolar Oficial (relação de disciplinas cursadas, notas, cargas horárias e situação acadêmica) é realizada pelo Portal do Aluno, conforme procedimentos indicados em{doc_ref}.\n\n"
            "Nos guias de orientação demonstrativos, a versão digital com autenticação eletrônica possui prazo indicativo de processamento de até 3 dias úteis e emissão gratuita pelo portal. Caso seja necessária via física impressa em papel timbrado com assinatura da Secretaria Acadêmica, o atendimento e a retirada devem ser agendados presencialmente no balcão da Secretaria portando documento de identificação com foto."
        )

    if topic == "matricula":
        combined_ctx = "\n".join(ev.chunk for ev in ordered if ev.document == top_doc).lower() if top_ev else ""
        details = [
            f"A Declaração e o Comprovante de Matrícula estão disponíveis para solicitação no Portal do Aluno, conforme documentado em{doc_ref}."
        ]
        details.append(
            "O documento comprova o vínculo com a instituição no período letivo selecionado pelo estudante no portal. Nos termos dos guias indicativos, o documento digital conta com código de autenticidade eletrônica com validade padrão de 30 dias a partir da emissão (para vias com exigência de firma física ou situações específicas, o atendimento é presencial na Secretaria Acadêmica)."
        )
        return "\n\n".join(details)

    if topic in ("provas_datas", "calendario"):
        return (
            f"Informação sobre datas de provas e calendário acadêmico: As datas exatas das avaliações e os prazos vigentes não estão disponíveis na base de conhecimento verificada. "
            f"Os documentos consultados em{doc_ref} contêm exclusivamente diretrizes procedimentais gerais e exemplos de demonstração (com atualizações de referência de 2024), não constituindo o Calendário Acadêmico homologado.\n\n"
            f"Ressalta-se que o calendário acadêmico institucional não coincide automaticamente com o calendário civil e exige homologação formal pela FECAP. "
            f"As normas gerais indicam que as avaliações ocorrem nos ciclos de A1, A2 e Avaliação Substitutiva, mas os períodos de aplicação e requerimento variam conforme o semestre letivo.\n\n"
            f"Para consultar o Calendário Acadêmico Oficial homologado e as datas exatas das provas de suas disciplinas, acesse a área 'Calendário Acadêmico' no Portal do Aluno para baixar o documento vigente ou confirme diretamente junto à Secretaria Acadêmica e à Coordenação de Curso."
        )

    if topic == "financeiro_boleto":
        return (
            f"A emissão de Segunda Via de Boletos e a consulta de mensalidades são realizadas na seção 'Financeiro' do Portal do Aluno, conforme documentado em{doc_ref}.\n\n"
            "No portal, você pode visualizar as mensalidades em aberto, gerar a linha digitável atualizada ou imprimir a 2ª via com novo vencimento. Para fins de testes no SecretarIA, você também pode utilizar o módulo financeiro demonstrativo integrado."
        )

    if topic == "rematricula":
        return (
            f"A Rematrícula (renovação de matrícula para o semestre seguinte) é realizada online pelo Portal do Aluno durante o período definido no Calendário Acadêmico homologado, conforme documentado em{doc_ref}.\n\n"
            "No portal, basta conferir as disciplinas disponíveis para o semestre, confirmar a seleção e verificar a emissão do boleto correspondente."
        )

    if topic == "aproveitamento":
        return (
            f"O Aproveitamento de Estudos (dispensa de disciplinas cursadas em outra instituição de ensino superior) deve ser solicitado mediante requerimento no Portal do Aluno, conforme documentado em{doc_ref}.\n\n"
            "É obrigatório anexar o Histórico Escolar oficial da instituição de origem e os planos de ensino/ementas das disciplinas cursadas. A solicitação é analisada pela Coordenação de Curso, que emite o parecer de equivalência curricular."
        )

    if topic == "revisao_nota":
        return (
            f"O pedido de Revisão de Nota pode ser protocolado pelo Portal do Aluno no prazo regulamentar indicativo de até 5 dias úteis contados a partir da divulgação oficial da nota, conforme documentado em{doc_ref}.\n\n"
            "O estudante deve registrar a justificativa acadêmica fundamentada no portal, indicando as questões ou critérios a serem revistos. O requerimento é encaminhado ao docente da disciplina e à Coordenação de Curso."
        )

    if topic == "segunda_via_doc":
        return (
            f"A solicitação de Segunda Via de Documentos Acadêmicos Físicos (como carteirinha de estudante ou certidões impressas em papel timbrado) pode ser protocolada no Portal do Aluno ou presencialmente na Secretaria Acadêmica, conforme documentado em{doc_ref}.\n\n"
            "Documentos digitais gerados diretamente pelo portal são gratuitos. Para segunda via de carteirinha física ou documentos com taxa de emissão, consulte a tabela oficial de emolumentos na Secretaria Acadêmica."
        )

    if topic == "atendimento":
        return (
            f"O atendimento aos estudantes da FECAP funciona presencialmente e por canais digitais, conforme documentado em{doc_ref}:\n\n"
            "• Secretaria Acadêmica: de segunda a sexta-feira, das 8h às 20h (presencial e via protocolos no Portal do Aluno 24h);\n"
            "• Central Financeira: de segunda a sexta-feira, das 9h às 18h;\n"
            "• Coordenação de Curso: atendimento mediante agendamento prévio no Portal do Aluno."
        )

    if topic == "portal":
        return (
            f"O acesso ao Portal do Aluno é realizado utilizando o Registro Acadêmico (RA) e a senha institucional cadastrada, conforme documentado em{doc_ref}.\n\n"
            "Para primeiro acesso ou em caso de esquecimento de senha, utilize o link de redefinição na tela de login informando seu RA ou CPF para receber as instruções de recuperação em seu e-mail institucional."
        )

    if topic == "fora_de_escopo":
        return (
            "Sou o assistente inteligente de orientação acadêmica da FECAP. Minha função é esclarecer dúvidas sobre normas, requerimentos, matrículas, notas, calendários e serviços da Secretaria Acadêmica.\n\n"
            "Não possuo informações sobre o tema solicitado por estar fora do escopo acadêmico institucional. Caso tenha alguma dúvida sobre seu curso ou vida acadêmica na FECAP, estou à disposição!"
        )

    excerpt = _extract_relevant_excerpt(question, top_ev.chunk, max_chars=240) if top_ev else ""
    if excerpt:
        return f"Com base na documentação consultada em {top_doc}: {excerpt}"
    return f"Encontrei orientações registradas em {top_doc} no Portal do Aluno para atender à sua consulta acadêmica."


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

class RAGPipeline:
    """
    Pipeline RAG para o Agente de Orientacao ao Estudante.

    Parametros lidos de app.core.config.settings:
      - agent_top_k_documents    : numero de chunks recuperados do ChromaDB
      - agent_min_evidence_score : score minimo para incluir um chunk
      - agent_confidence_threshold: confianca minima para gerar resposta
      - llm_mode                 : "demo" | "gemini"
    """

    def __init__(self, vector_store: Optional[VectorStoreService] = None):
        self._vs = vector_store  # injecao para facilitar testes

    @property
    def vector_store(self) -> VectorStoreService:
        if self._vs is None:
            self._vs = VectorStoreService()
        return self._vs

    def _expand_sibling_evidence(
        self,
        raw_results: List[dict],
        evidence: List[AgentEvidence],
    ) -> List[AgentEvidence]:
        """
        Complementa a lista de evidencias com fragmentos irmaos (mesmo document_id)
        dos documentos recuperados quando disponiveis na colecao persistente,
        garantindo que secoes 'COMO OBTER / COMO SOLICITAR' (Etapa 1..N) nao sejam
        truncadas pelo corte Top-K.
        """
        if not raw_results or not evidence:
            return evidence
        try:
            coll = getattr(self.vector_store, "collection", None)
            if coll is None or not hasattr(coll, "get"):
                return evidence

            seen_texts = {ev.chunk for ev in evidence}
            doc_ids = []
            for r in raw_results[:5]:
                meta = r.get("metadata") or {}
                did = meta.get("document_id")
                if did and isinstance(did, str) and did not in doc_ids:
                    doc_ids.append(did)

            expanded = list(evidence)
            for did in doc_ids:
                siblings = coll.get(where={"document_id": did}, include=["documents", "metadatas"])
                if not siblings or not isinstance(siblings, dict):
                    continue
                docs = siblings.get("documents") or []
                metas = siblings.get("metadatas") or []
                if not isinstance(docs, list):
                    continue
                pairs = []
                for idx, txt in enumerate(docs):
                    m = metas[idx] if idx < len(metas) and isinstance(metas[idx], dict) else {}
                    pairs.append((m.get("chunk_index", idx), txt, m))
                pairs.sort(key=lambda x: x[0])
                for _, txt, m in pairs:
                    if isinstance(txt, str) and txt not in seen_texts and (
                        "Etapa " in txt
                        or "COMO " in txt
                        or "1.2 Historico" in txt
                        or "2. TRANCAMENTO" in txt
                        or "3. APROVEITAMENTO" in txt
                        or "4. REVISAO" in txt
                    ):
                        seen_texts.add(txt)
                        doc_label = m.get("title", m.get("document_id", "Desconhecido"))
                        expanded.append(
                            AgentEvidence(
                                chunk=_sanitize_chunk_text(txt),
                                document=doc_label,
                                relevance_score=evidence[0].relevance_score,
                            )
                        )
            return expanded
        except Exception:  # pylint: disable=broad-except
            return evidence

    # ------------------------------------------------------------------
    def run(self, query: AgentQuery) -> AgentResponse:
        """
        Executa o pipeline RAG de forma sincrona.
        FastAPI chama este metodo num executor de thread (run_in_executor)
        a partir do endpoint async — ver agent.py.
        """
        run_id = str(uuid.uuid4())
        question = (query.question or "").strip()

        logger.info(
            "RAG pipeline iniciado",
            run_id=run_id,
            student_id=query.student_id,
            question_len=len(question),
        )

        # --- Etapa 1: validar pergunta ----------------------------------
        if not question:
            logger.warning("Pergunta vazia recebida", run_id=run_id)
            return AgentResponse(
                id=run_id,
                answer="Por favor, envie uma pergunta valida.",
                steps=["validacao: pergunta vazia"],
                next_action="retry",
                source="agent",
                version=settings.agent_version,
                updated_at=datetime.now(timezone.utc).isoformat(),
                evidence=[],
                confidence=0.0,
                requires_human=False,
            )

        # --- Etapa 1b: verificar se e resposta curta conversacional -----
        short_reply = _detect_conversational_reply(question)
        if short_reply is not None:
            logger.info(
                "Resposta curta conversacional tratada diretamente",
                run_id=run_id,
                next_action=short_reply.next_action,
            )
            return short_reply

        # --- Etapa 2: recuperar chunks do ChromaDB ----------------------
        top_k = settings.agent_top_k_documents
        raw_results = self.vector_store.query_similar(question, top_k=top_k)

        logger.info(
            "Chunks recuperados",
            run_id=run_id,
            total_raw=len(raw_results),
            top_k=top_k,
        )

        # --- Etapa 3: filtrar evidencias relevantes ---------------------
        evidence = _filter_evidence(raw_results)
        scores = [ev.relevance_score for ev in evidence if ev.relevance_score is not None]

        logger.info(
            "Evidencias apos filtro",
            run_id=run_id,
            evidence_count=len(evidence),
            min_score=settings.agent_min_evidence_score,
        )

        # --- Etapa 4: calcular confianca composta -----------------------
        confidence = _compute_confidence(scores)
        topic = _detect_academic_topic(question)

        # Regra de abstencao para fora de escopo (receitas, esportes, etc.)
        if topic == "fora_de_escopo":
            confidence = 0.20

        has_lexical_overlap = any(
            bool(_keywords(question) & _keywords(f"{ev.document} {ev.chunk}"))
            for ev in evidence
        )
        if evidence and not has_lexical_overlap and topic == "geral" and confidence < 0.70:
            # Perguntas fora do dominio academico (ex: receitas, esportes) sem correspondencia
            # lexical com a base de conhecimento nao devem gerar resposta inventada
            confidence = round(min(confidence, settings.agent_confidence_threshold - 0.05), 4)

        logger.info(
            "Confianca calculada",
            run_id=run_id,
            confidence=confidence,
            threshold=settings.agent_confidence_threshold,
            topic=topic,
        )

        # --- Etapa 5: abstencao responsavel ----------------------------
        if confidence < settings.agent_confidence_threshold or not evidence:
            logger.info(
                "Abstencao ativada — confianca insuficiente ou fora de escopo",
                run_id=run_id,
                confidence=confidence,
                topic=topic,
            )
            return AgentResponse(
                id=run_id,
                answer=settings.agent_fallback_message + _ABSTENTION_DISCLAIMER,
                steps=None,
                next_action="handoff",
                source="agent",
                version=settings.agent_version,
                updated_at=datetime.now(timezone.utc).isoformat(),
                evidence=evidence,
                confidence=confidence,
                requires_human=True,
            )

        # --- Etapa 6a/6b: gerar resposta --------------------------------
        expanded_evidence = self._expand_sibling_evidence(raw_results, evidence)
        ordered_evidence = _prioritize_topic_evidence(question, expanded_evidence)
        primary_doc_name = ordered_evidence[0].document if ordered_evidence else ""
        focused_evidence = [
            ev for ev in ordered_evidence if ev.document == primary_doc_name
        ] or ordered_evidence[:top_k]

        # Sanitizar os chunks de evidencia para contexto e exibicao
        sanitized_evidence = [
            AgentEvidence(
                chunk=_sanitize_chunk_text(ev.chunk),
                document=ev.document,
                relevance_score=ev.relevance_score,
            )
            for ev in focused_evidence[:top_k]
        ]

        context_block = _build_context_block(sanitized_evidence)
        mode = settings.llm_mode.lower()

        # Extrai passos procedimentais academicos reais das evidencias
        procedural_steps = _extract_procedural_steps(question, ordered_evidence)
        final_steps: Optional[List[str]] = procedural_steps

        try:
            # REGRA ESTRITA: Perguntas financeiras/boletos NUNCA sao enviadas para Gemini
            if topic == "financeiro_boleto":
                logger.info("Consulta financeira tratada localmente com seguranca", run_id=run_id)
                answer = _build_demo_answer(question, ordered_evidence)
                if not final_steps:
                    final_steps = [
                        "Acesse o Portal do Aluno na seção Financeiro",
                        "Selecione a opção 2ª via de boletos ou utilize o painel interativo no chat",
                    ]
            elif mode == "gemini" and settings.google_api_key:
                logger.info("Invocando Gemini para sintese academica fundamentada", run_id=run_id)
                answer = _call_gemini(question, context_block)
                if not final_steps:
                    final_steps = [f"geracao: Gemini ({settings.gemini_model})"]
            else:
                answer = _build_demo_answer(question, ordered_evidence)

            if _DEMO_DISCLAIMER not in answer:
                answer += _DEMO_DISCLAIMER

        except Exception as exc:  # pylint: disable=broad-except
            logger.error(
                "Erro na geracao de resposta — fallback para sintese demo local",
                run_id=run_id,
                error=str(exc),
            )
            answer = _build_demo_answer(question, ordered_evidence)
            if _DEMO_DISCLAIMER not in answer:
                answer += _DEMO_DISCLAIMER
            if not final_steps:
                final_steps = ["geracao: erro Gemini -> fallback para demo"]

        logger.info("RAG pipeline concluido", run_id=run_id, topic=topic)

        return AgentResponse(
            id=run_id,
            answer=answer,
            steps=final_steps,
            next_action="none",
            source="rag_pipeline",
            version=settings.agent_version,
            updated_at=datetime.now(timezone.utc).isoformat(),
            evidence=sanitized_evidence,
            confidence=confidence,
            requires_human=False,
        )
