"""
Gerador e Servidor de Documentos PDF de Demonstração (SecretarIA / FECAP Guia).

Gera arquivos PDF válidos (Padrão ISO PDF-1.4 com fontes Type1 nativas Helvetica / Helvetica-Bold)
para download real no navegador.

REGRAS DE GOVERNANÇA E CONFORMIDADE:
1. Todos os documentos trazem em destaque a marcação:
   "DOCUMENTO FICTÍCIO — DEMONSTRAÇÃO ACADÊMICA — SEM VALIDADE OFICIAL"
2. Nenhum documento apresenta assinaturas institucionais, QR Codes de validação
   ou autenticações da FECAP como reais.
3. Retorna Content-Type: application/pdf e Content-Disposition: attachment; filename="...".
"""
from __future__ import annotations

from datetime import datetime, timezone
import re
import textwrap
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, record_audit_log, security_scheme
from app.models.entities import KnowledgeDocument, User

router = APIRouter()

MANDATORY_FICTITIOUS_STAMP = "DOCUMENTO FICTÍCIO — DEMONSTRAÇÃO ACADÊMICA — SEM VALIDADE OFICIAL"

# Catálogo de documentos PDF de demonstração disponíveis no SecretarIA
DEMO_DOCUMENTS_CATALOG: Dict[str, dict] = {
    "comprovante_matricula_2026_1_fecap.pdf": {
        "filename": "Comprovante_Matricula_2026_1_FECAP.pdf",
        "title": "Guia e Modelo de Comprovante de Matrícula (2026/1)",
        "category": "Documentos e Certidões (Simulação)",
        "body": [
            "FINALIDADE DESTE ARQUIVO DE DEMONSTRAÇÃO:",
            "Este documento ilustra o modelo orientativo de Declaração / Comprovante de Matrícula "
            "para fins de demonstração do sistema acadêmico SecretarIA (FECAP Guia).",
            "",
            "DADOS FICTÍCIOS DO ESTUDANTE (AMBIENTE DEMO):",
            "• Nome: Ana Silva (Perfil Fictício de Teste)",
            "• RA Simulado: 202612345",
            "• Curso Simulado: Bacharelado em Ciências Contábeis / Administração",
            "• Período Letivo de Referência: 2026/1",
            "",
            "COMO EMITIR O DOCUMENTO REAL NO PORTAL DO ALUNO:",
            "1. Acesse o Portal do Aluno com suas credenciais institucionais.",
            "2. Navegue até o menu lateral 'Documentos' > 'Declaração de Matrícula'.",
            "3. Selecione o semestre letivo vigente e solicite a emissão do arquivo.",
            "",
            "AVISO DE TRANSPARÊNCIA INSTITUCIONAL:",
            "Este PDF foi gerado pelo ambiente de demonstração acadêmica do projeto SecretarIA. "
            "Não possui assinatura digital, código de autenticação nem validade perante a FECAP "
            "ou terceiros.",
        ],
    },
    "historico_escolar_oficial_fecap.pdf": {
        "filename": "Historico_Escolar_Demonstracao_FECAP.pdf",
        "title": "Roteiro e Modelo Demonstrativo de Histórico Escolar",
        "category": "Secretaria Acadêmica (Simulação)",
        "body": [
            "FINALIDADE DESTE ARQUIVO DE DEMONSTRAÇÃO:",
            "Este PDF apresenta um espelho meramente ilustrativo de Histórico Escolar e o passo a passo "
            "para solicitação no Portal do Aluno.",
            "",
            "RESUMO ACADÊMICO SIMULADO (DADOS FICTÍCIOS):",
            "• Estudante: Ana Silva (RA Simulado 202612345)",
            "• Disciplina Fictícia 01: Contabilidade Geral — Nota: 8,5 — Frequência: 92% (Simulado)",
            "• Disciplina Fictícia 02: Matemática Financeira — Nota: 9,0 — Frequência: 95% (Simulado)",
            "• Disciplina Fictícia 03: Direito Empresarial — Nota: 8,0 — Frequência: 88% (Simulado)",
            "",
            "PROCEDIMENTO PARA EMISSÃO NO PORTAL DO ALUNO:",
            "1. Acesse Portal do Aluno > Menu Documentos > Histórico Escolar.",
            "2. Escolha a modalidade desejada (Simples Conferência ou Solicitação de Histórico).",
            "3. Acompanhe o processamento conforme prazos vigentes da Secretaria Acadêmica (ASA).",
            "",
            "AVISO DE TRANSPARÊNCIA INSTITUCIONAL:",
            "Este arquivo é um modelo fictício de demonstração acadêmica. Nenhuma nota, frequência "
            "ou validação institucional constante neste PDF é real.",
        ],
    },
    "boleto_mensalidade_marco_2026.pdf": {
        "filename": "Boleto_Demonstracao_Marco_2026.pdf",
        "title": "Demonstrativo Financeiro e Instruções de 2ª Via (Simulação)",
        "category": "Financeiro (Simulação)",
        "body": [
            "FINALIDADE DESTE ARQUIVO DE DEMONSTRAÇÃO:",
            "Documento demonstrativo para simular o fluxo de consulta de 2ª via de boleto e instruções "
            "financeiras no projeto acadêmico SecretarIA.",
            "",
            "DADOS SIMULADOS (SEM VALOR DE COBRANÇA):",
            "• Aluno(a) Fictício(a): Ana Silva (RA 202612345)",
            "• Competência Ilustrativa: Março / 2026",
            "• Linha Digitável Fictícia: 00000.00000 00000.000000 00000.000000 0 00000000000000",
            "• Status: DEMONSTRAÇÃO ACADÊMICA (NÃO UTILIZAR PARA PAGAMENTO)",
            "",
            "PASSO A PASSO PARA 2ª VIA REAL NO PORTAL DO ALUNO:",
            "1. Acesse Portal do Aluno > Menu Financeiro > Boletos e Mensalidades.",
            "2. Identifique a parcela correspondente ao mês de referência.",
            "3. Utilize as opções oficiais do Portal para visualizar o boleto ou PIX institucional.",
            "",
            "AVISO DE TRANSPARÊNCIA INSTITUCIONAL:",
            "Este PDF não é um boleto bancário verdadeiro e não possui vínculo com o sistema "
            "financeiro da FECAP.",
        ],
    },
    "calendario_academico_graduacao_2026.pdf": {
        "filename": "Calendario_Academico_Demonstracao_2026.pdf",
        "title": "Calendário Acadêmico Demonstrativo — Graduação 2026/1",
        "category": "Pró-Reitoria / Acadêmico (Simulação)",
        "body": [
            "DATAS DE REFERÊNCIA (CONTEÚDO DEMONSTRATIVO DO PROJETO):",
            "• Início das Aulas (1º Semestre): 09/02/2026 (Data Fictícia de Demonstração)",
            "• Prazo Limite para Trancamento Voluntário: até 30 dias após o início letivo",
            "• Período de Avaliações Regimentais A1: 06/04/2026 a 11/04/2026",
            "• Período de Avaliações Regimentais A2: 08/06/2026 a 13/06/2026",
            "• Avaliações Substitutivas: 22/06/2026 a 26/06/2026 (mediante requerimento prévio)",
            "• Período de Rematrícula de Veteranos: 01/07/2026 a 15/07/2026",
            "",
            "RECOMENDAÇÃO AO ESTUDANTE:",
            "Consulte sempre o Calendário Acadêmico vigente diretamente no Portal do Aluno ou "
            "junto à Secretaria Acadêmica (ASA).",
            "",
            "AVISO DE TRANSPARÊNCIA INSTITUCIONAL:",
            "Este cronograma integra a base de testes do projeto SecretarIA e não substitui "
            "publicações oficiais da instituição.",
        ],
    },
    "calendario_academico_oficial_2026_1.pdf": {
        "filename": "Calendario_Academico_Demonstracao_2026_1.pdf",
        "title": "Calendário Acadêmico Demonstrativo — 2026/1",
        "category": "Pró-Reitoria / Acadêmico (Simulação)",
        "body": [
            "DATAS DE REFERÊNCIA (CONTEÚDO DEMONSTRATIVO DO PROJETO):",
            "• Início das Aulas (1º Semestre): 09/02/2026 (Data Fictícia de Demonstração)",
            "• Avaliações Regimentais A1: 06/04/2026 a 11/04/2026",
            "• Avaliações Regimentais A2: 08/06/2026 a 13/06/2026",
            "• Avaliações Substitutivas: 22/06/2026 a 26/06/2026",
            "• Rematrícula: 01/07/2026 a 15/07/2026",
            "",
            "AVISO DE TRANSPARÊNCIA INSTITUCIONAL:",
            "Documento fictício elaborado exclusivamente para testes de download no projeto SecretarIA.",
        ],
    },
    "formulario_trancamento_matricula_fecap.pdf": {
        "filename": "Formulario_Trancamento_Demonstracao_FECAP.pdf",
        "title": "Guia e Requerimento Demonstrativo de Trancamento de Matrícula",
        "category": "Secretaria Geral (Simulação)",
        "body": [
            "ORIENTAÇÕES DE DEMONSTRAÇÃO SOBRE TRANCAMENTO DE MATRÍCULA:",
            "1. O pedido de trancamento deve ser protocolado diretamente no Portal do Aluno > Requerimentos.",
            "2. Verifique os prazos do Calendário Acadêmico vigente para solicitação sem ônus de parcelas vincendas.",
            "3. Acompanhe o parecer do setor responsável pelo número de protocolo gerado no Portal.",
            "",
            "AVISO DE TRANSPARÊNCIA INSTITUCIONAL:",
            "Este formulário é um modelo fictício de demonstração acadêmica e não protocola "
            "solicitações reais junto à FECAP.",
        ],
    },
    "regimento_geral_fecap_2026.pdf": {
        "filename": "Resumo_Regimento_Demonstracao_2026.pdf",
        "title": "Compêndio Demonstrativo de Normas Acadêmicas (Projeto SecretarIA)",
        "category": "Secretaria Geral (Simulação)",
        "body": [
            "RESUMO ORIENTATIVO PARA DEMONSTRAÇÃO DO AGENTE RAG:",
            "• Capítulo I — Trancamento e Cancelamento de Matrícula: normas simuladas de prazos e procedimentos.",
            "• Capítulo II — Avaliações Regimentais (A1, A2 e Substitutiva): critérios simulados de média e frequência.",
            "• Capítulo III — Aproveitamento de Estudos e Equivalência: regras simuladas para análise de ementas.",
            "• Capítulo IV — Emissão de Documentos Escolares: orientações para uso do Portal do Aluno.",
            "• Capítulo V — Disposições Financeiras: orientações para emissão de 2ª via e acordos.",
            "",
            "AVISO DE TRANSPARÊNCIA INSTITUCIONAL:",
            "Texto sintético para avaliação acadêmica do sistema SecretarIA. Não possui valor normativo oficial.",
        ],
    },
    "manual_do_estudante_graduacao_2026.pdf": {
        "filename": "Manual_do_Estudante_Demonstracao_2026.pdf",
        "title": "Manual do Estudante — Edição de Demonstração Acadêmica",
        "category": "Acadêmico (Simulação)",
        "body": [
            "BEM-VINDO AO GUIA DE DEMONSTRAÇÃO DO ESTUDANTE:",
            "• Canais de Atendimento: Portal do Aluno e Secretaria Acadêmica (ASA).",
            "• Autoatendimento Digital: consulta de notas, faltas, requerimentos e boletos.",
            "• Atendimento Assistido: encaminhamento por protocolo quando a dúvida exigir análise específica.",
            "",
            "AVISO DE TRANSPARÊNCIA INSTITUCIONAL:",
            "Documento fictício de demonstração acadêmica, sem validade oficial.",
        ],
    },
    "manual_normas_aacc_horas_complementares.pdf": {
        "filename": "Manual_AACC_Horas_Complementares_Demonstracao.pdf",
        "title": "Guia Demonstrativo de Atividades Complementares (AACC)",
        "category": "Coordenações (Simulação)",
        "body": [
            "ORIENTAÇÕES SIMULADAS SOBRE HORAS COMPLEMENTARES (AACC):",
            "• Envie os certificados em formato PDF pelo Portal do Aluno > Atividades Complementares.",
            "• Selecione a modalidade correspondente (cursos, palestras, iniciação científica, extensão).",
            "• Acompanhe o cômputo de horas no extrato acadêmico do Portal.",
            "",
            "AVISO DE TRANSPARÊNCIA INSTITUCIONAL:",
            "Documento fictício de demonstração acadêmica, sem validade oficial.",
        ],
    },
    "politica_descontos_e_bolsas_2026.pdf": {
        "filename": "Politica_Descontos_e_Bolsas_Demonstracao_2026.pdf",
        "title": "Informativo Demonstrativo de Bolsas e Financiamentos",
        "category": "Financeiro (Simulação)",
        "body": [
            "INFORMAÇÕES SIMULADAS SOBRE BOLSAS E DESCONTOS:",
            "• Consulte editais vigentes e condições de renovação semestral no Portal do Aluno.",
            "• Descontos de pontualidade e convênios seguem regras específicas do setor financeiro.",
            "",
            "AVISO DE TRANSPARÊNCIA INSTITUCIONAL:",
            "Documento fictício de demonstração acadêmica, sem validade oficial.",
        ],
    },
}


def _escape_pdf_text(text: str) -> str:
    """Converte string UTF-8 para bytes WinAnsi/Latin-1 seguros na sintaxe literal do PDF."""
    latin_bytes = text.encode("cp1252", errors="replace")
    out: List[str] = []
    for b in latin_bytes:
        ch = chr(b)
        if ch == "\\":
            out.append("\\\\")
        elif ch == "(":
            out.append("\\(")
        elif ch == ")":
            out.append("\\)")
        elif 32 <= b <= 126:
            out.append(ch)
        else:
            out.append(f"\\{b:03o}")
    return "".join(out)


def build_fictitious_demo_pdf(
    title: str,
    category: str,
    body_paragraphs: List[str],
    doc_key: str,
    stamp: Optional[str] = None,
) -> bytes:
    """
    Constrói um arquivo PDF 1.4 binário válido e autossuficiente (sem depender de bibliotecas C externas),
    contendo cabeçalho institucional de demonstração e carimbo obrigatório:
    'DOCUMENTO FICTÍCIO — DEMONSTRAÇÃO ACADÊMICA — SEM VALIDADE OFICIAL'.
    """
    now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    stamp = stamp or MANDATORY_FICTITIOUS_STAMP
    stamp_size = min(10.5, 495 / (len(stamp) * 0.60))

    stream_ops: List[str] = []

    # Fundo do banner superior de aviso (retângulo cinza claro com borda)
    stream_ops.append("0.95 0.96 0.95 rg")
    stream_ops.append("0.15 0.45 0.32 RG")
    stream_ops.append("1.2 w")
    stream_ops.append("45 745 505 58 re B")

    # Carimbo obrigatório em destaque no topo
    stream_ops.append("BT")
    stream_ops.append(f"/F2 {stamp_size:.2f} Tf")
    stream_ops.append("0.75 0.12 0.12 rg")
    stream_ops.append(f"55 785 Td ({_escape_pdf_text(stamp)}) Tj")
    stream_ops.append("ET")

    stream_ops.append("BT")
    stream_ops.append("/F1 8.5 Tf")
    stream_ops.append("0.20 0.25 0.22 rg")
    stream_ops.append(
        f"55 768 Td ({_escape_pdf_text('Projeto Acadêmico SecretarIA / FECAP Guia — Ambiente de Simulação sem Integração Oficial')}) Tj"
    )
    stream_ops.append("ET")

    stream_ops.append("BT")
    stream_ops.append("/F1 8 Tf")
    stream_ops.append(
        f"55 754 Td ({_escape_pdf_text(f'Categoria: {category}   |   Gerado em: {now_str}   |   Ref: {doc_key}')}) Tj"
    )
    stream_ops.append("ET")

    # Título do documento
    stream_ops.append("BT")
    stream_ops.append("/F2 13 Tf")
    stream_ops.append("0.0 0.30 0.20 rg")
    stream_ops.append(f"45 718 Td ({_escape_pdf_text(title)}) Tj")
    stream_ops.append("ET")

    # Linha divisória
    stream_ops.append("0.75 0.80 0.78 RG")
    stream_ops.append("0.8 w")
    stream_ops.append("45 708 m 550 708 l S")

    # Corpo do texto com quebra automática de linha
    y = 688
    for paragraph in body_paragraphs:
        if not paragraph.strip():
            y -= 10
            continue

        is_heading = paragraph.isupper() and paragraph.endswith(":")
        wrapped_lines = textwrap.wrap(paragraph, width=82) or [paragraph]

        for line in wrapped_lines:
            if y < 95:
                break
            font_tag = "/F2" if is_heading else "/F1"
            font_size = 9.5 if is_heading else 9.5
            color_cmd = "0.05 0.25 0.18 rg" if is_heading else "0.12 0.14 0.16 rg"

            stream_ops.append("BT")
            stream_ops.append(f"{font_tag} {font_size} Tf")
            stream_ops.append(color_cmd)
            stream_ops.append(f"45 {y} Td ({_escape_pdf_text(line)}) Tj")
            stream_ops.append("ET")
            y -= 14

    # Rodapé obrigatório repetindo que o documento é fictício e sem assinatura real
    stream_ops.append("0.75 0.80 0.78 RG")
    stream_ops.append("0.8 w")
    stream_ops.append("45 76 m 550 76 l S")

    stream_ops.append("BT")
    stream_ops.append(f"/F2 {min(8.5, stamp_size):.2f} Tf")
    stream_ops.append("0.75 0.12 0.12 rg")
    stream_ops.append(f"45 60 Td ({_escape_pdf_text(stamp)}) Tj")
    stream_ops.append("ET")

    stream_ops.append("BT")
    stream_ops.append("/F1 7.5 Tf")
    stream_ops.append("0.35 0.38 0.40 rg")
    stream_ops.append(
        f"45 47 Td ({_escape_pdf_text('Aviso: Este arquivo não contém assinatura digital nem validação institucional da FECAP.')}) Tj"
    )
    stream_ops.append("ET")

    content_stream = "\n".join(stream_ops).encode("latin-1", errors="replace")

    objects: List[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> "
            b"/Contents 6 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
        b"<< /Length "
        + str(len(content_stream)).encode("ascii")
        + b" >>\nstream\n"
        + content_stream
        + b"\nendstream",
    ]

    pdf_parts: List[bytes] = [b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"]
    offsets: List[int] = []
    current_offset = len(pdf_parts[0])

    for idx, obj_body in enumerate(objects, start=1):
        offsets.append(current_offset)
        obj_Block = f"{idx} 0 obj\n".encode("ascii") + obj_body + b"\nendobj\n"
        pdf_parts.append(obj_Block)
        current_offset += len(obj_Block)

    xref_offset = current_offset
    xref_lines = [f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii")]
    for off in offsets:
        xref_lines.append(f"{off:010d} 00000 n \n".encode("ascii"))

    trailer = (
        b"".join(xref_lines)
        + f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
            "ascii"
        )
    )
    pdf_parts.append(trailer)
    return b"".join(pdf_parts)


def _normalize_doc_key(raw_name: str) -> str:
    """Normaliza o nome do arquivo solicitado e valida contra path traversal."""
    cleaned = (raw_name or "").strip()
    if not cleaned or ".." in cleaned or "/" in cleaned or "\\" in cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nome de documento inválido.",
        )
    lower = cleaned.lower()
    if not lower.endswith(".pdf"):
        lower = f"{lower}.pdf"
    return lower


@router.get("/", status_code=status.HTTP_200_OK)
async def list_available_demo_pdfs() -> dict:
    """Lista os documentos PDF de demonstração disponíveis para download."""
    items = [
        {
            "key": key,
            "filename": meta["filename"],
            "title": meta["title"],
            "category": meta["category"],
            "disclaimer": MANDATORY_FICTITIOUS_STAMP,
        }
        for key, meta in DEMO_DOCUMENTS_CATALOG.items()
    ]
    return {"documents": items, "count": len(items)}


@router.get("/download/{doc_name}", status_code=status.HTTP_200_OK)
async def download_demo_pdf(
    doc_name: str,
    require_auth: bool = Query(default=False, description="Se true, exige token JWT válido."),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Gera e fornece o download real de um documento PDF de demonstração.
    - Se um header Authorization Bearer for enviado (ou se require_auth=True), valida o JWT (retorna 401 se inválido/expirado).
    - Retorna 404 se o documento não existir no catálogo nem na base de conhecimento.
    - Define Content-Type: application/pdf e Content-Disposition: attachment; filename="...".
    """
    current_user: Optional[User] = None
    if credentials and credentials.credentials:
        current_user = await get_current_user(credentials=credentials, db=db)
    elif require_auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação necessária para baixar este documento.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    normalized_key = _normalize_doc_key(doc_name)
    catalog_entry = DEMO_DOCUMENTS_CATALOG.get(normalized_key)

    # Permite resolução flexível por filename (ex: Historico_Escolar_Demonstracao_FECAP.pdf)
    if catalog_entry is None:
        for k, v in DEMO_DOCUMENTS_CATALOG.items():
            if v.get("filename", "").lower() == normalized_key:
                catalog_entry = v
                normalized_key = k
                break

    if catalog_entry is None:
        # Procura também na tabela knowledge_documents pelo título ou file_path
        base_title = re.sub(r"\.pdf$", "", normalized_key, flags=re.IGNORECASE).replace("_", " ")
        stmt = select(KnowledgeDocument).where(
            (KnowledgeDocument.file_path.ilike(f"%{normalized_key}%"))
            | (KnowledgeDocument.title.ilike(f"%{base_title}%"))
        )
        res = await db.execute(stmt)
        kb_doc = res.scalars().first()

        if kb_doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documento PDF '{doc_name}' não encontrado no catálogo de demonstração.",
            )

        safe_filename = re.sub(r"[^a-zA-Z0-9_\-.]", "_", kb_doc.title)
        if not safe_filename.lower().endswith(".pdf"):
            safe_filename += ".pdf"

        paragraphs = [p.strip() for p in (kb_doc.content or "").split("\n") if p.strip()]
        paragraphs.append("")
        paragraphs.append("AVISO DE TRANSPARÊNCIA INSTITUCIONAL:")
        paragraphs.append(MANDATORY_FICTITIOUS_STAMP)

        pdf_bytes = build_fictitious_demo_pdf(
            title=f"{kb_doc.title} (Versão {kb_doc.version})",
            category=f"{kb_doc.category} (Simulação)",
            body_paragraphs=paragraphs,
            doc_key=normalized_key,
        )
        download_filename = safe_filename
    else:
        pdf_bytes = build_fictitious_demo_pdf(
            title=catalog_entry["title"],
            category=catalog_entry["category"],
            body_paragraphs=catalog_entry["body"],
            doc_key=normalized_key,
        )
        download_filename = catalog_entry["filename"]

    await record_audit_log(
        db=db,
        action="pdf_downloaded",
        resource="documents_pdf",
        detail=f"Download de PDF demonstrativo '{download_filename}' ({len(pdf_bytes)} bytes)",
        user_id=current_user.id if current_user else None,
    )

    headers = {
        "Content-Disposition": f'attachment; filename="{download_filename}"',
        "Content-Length": str(len(pdf_bytes)),
        "X-Document-Disclaimer": "DOCUMENTO FICTICIO - DEMONSTRACAO ACADEMICA - SEM VALIDADE OFICIAL",
        "Cache-Control": "no-store",
    }

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers=headers,
    )
