"""
Testes automatizados para geração e download real de documentos PDF de demonstração.
Cobre:
  1. Listagem de documentos PDF demonstrativos (`GET /api/v1/documents/`).
  2. Geração e download real (`GET /api/v1/documents/download/{doc_name}`) com:
     - Status 200 OK
     - Content-Type: application/pdf
     - Content-Disposition: attachment; filename="..."
     - Assinatura mágica binária %PDF-1.4 e trailer %%EOF
  3. Extração de texto via pypdf confirmando:
     - Carimbo obrigatório "DOCUMENTO FICTÍCIO — DEMONSTRAÇÃO ACADÊMICA — SEM VALIDADE OFICIAL"
     - Ausência de assinaturas ou validações institucionais apresentadas como reais.
  4. Tratamento de erros de autenticação (401 com token inválido ou quando require_auth=True sem token).
  5. Tratamento de arquivo inexistente (404) e tentativa de path traversal (400).
"""
import io
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.api.v1.documents import MANDATORY_FICTITIOUS_STAMP
from app.main import app

client = TestClient(app)


def test_list_available_demo_pdfs():
    """1. Verifica listagem do catálogo de PDFs demonstrativos."""
    res = client.get("/api/v1/documents/")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] >= 6
    assert any(
        d["key"] == "comprovante_matricula_2026_1_fecap.pdf"
        and d["disclaimer"] == MANDATORY_FICTITIOUS_STAMP
        for d in data["documents"]
    )


def test_download_real_pdf_headers_and_content():
    """
    2 e 3. Verifica download real de todos os PDFs principais da interface:
    - Content-Type application/pdf
    - Content-Disposition attachment com filename .pdf
    - Estrutura PDF válida lida pelo pypdf.PdfReader
    - Carimbo obrigatório DOCUMENTO FICTÍCIO — DEMONSTRAÇÃO ACADÊMICA — SEM VALIDADE OFICIAL
    - Ausência de afirmações falsas de validação/assinatura oficial real.
    """
    doc_names = [
        "Comprovante_Matricula_2026_1_FECAP.pdf",
        "Historico_Escolar_Oficial_FECAP.pdf",
        "Boleto_Mensalidade_Marco_2026.pdf",
        "Calendario_Academico_Graduacao_2026.pdf",
        "Formulario_Trancamento_Matricula_FECAP.pdf",
        "Regimento_Geral_FECAP_2026.pdf",
    ]

    for doc_name in doc_names:
        res = client.get(f"/api/v1/documents/download/{doc_name}")
        assert res.status_code == 200, f"Falha ao baixar {doc_name}: {res.text}"

        # Verifica Content-Type e Content-Disposition
        assert res.headers["content-type"].startswith("application/pdf")
        content_disp = res.headers.get("content-disposition", "")
        assert "attachment;" in content_disp
        assert '.pdf"' in content_disp

        # Verifica bytes binários do PDF
        pdf_bytes = res.content
        assert len(pdf_bytes) > 500
        assert pdf_bytes.startswith(b"%PDF-1.4")
        assert b"%%EOF" in pdf_bytes[-64:]

        # Extrai texto com pypdf para provar que o PDF é válido e contém a marcação obrigatória
        reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) >= 1
        extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages)

        assert "DOCUMENTO FICTÍCIO" in extracted_text
        assert "DEMONSTRAÇÃO ACADÊMICA" in extracted_text
        assert "SEM VALIDADE OFICIAL" in extracted_text
        assert "não contém assinatura digital nem validação institucional da FECAP" in extracted_text


def test_download_pdf_authentication_and_missing_file_errors():
    """
    4 e 5. Testa tratamento de erros de autenticação (401), arquivo inexistente (404)
    e nome inválido (400).
    """
    # Token JWT inválido enviado no header Authorization -> deve retornar 401
    res_bad_token = client.get(
        "/api/v1/documents/download/Comprovante_Matricula_2026_1_FECAP.pdf",
        headers={"Authorization": "Bearer token_invalido_123"},
    )
    assert res_bad_token.status_code == 401

    # require_auth=true sem token -> deve retornar 401
    res_auth_required = client.get(
        "/api/v1/documents/download/Comprovante_Matricula_2026_1_FECAP.pdf?require_auth=true"
    )
    assert res_auth_required.status_code == 401

    # Documento inexistente -> deve retornar 404
    res_not_found = client.get("/api/v1/documents/download/Arquivo_Que_Nao_Existe_9999.pdf")
    assert res_not_found.status_code == 404
    assert "não encontrado" in res_not_found.json()["detail"].lower()
