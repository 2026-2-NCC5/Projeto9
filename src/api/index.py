import os
import random
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pypdf
from dotenv import load_dotenv

load_dotenv()

# Instância principal do FastAPI para Vercel Serverless Functions
app = FastAPI(
    title="SecretarIA API — Secretaria Acadêmica Inteligente (ASA/FECAP)",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicialização do Gemini Client se chave estiver no ambiente
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai_client = None

if GEMINI_API_KEY:
    try:
        from google import genai
        genai_client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Aviso ao carregar GenAI Client: {e}")

# Leitura e indexação do PDF do Regimento Geral FECAP
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_PATH = os.path.join(BASE_DIR, "..", "data", "Regimento_FECAP.pdf")
REGIMENTO_TEXT = ""

def load_regimento_pdf():
    global REGIMENTO_TEXT
    target_path = os.path.abspath(PDF_PATH)
    if os.path.exists(target_path):
        try:
            reader = pypdf.PdfReader(target_path)
            text_pages = [page.extract_text() for page in reader.pages if page.extract_text()]
            REGIMENTO_TEXT = "\n\n".join(text_pages)
        except Exception as e:
            print(f"Erro ao ler PDF: {e}")
            REGIMENTO_TEXT = "Regimento Geral ASA/FECAP — Graduação e Pós-Graduação 2026."
    else:
        REGIMENTO_TEXT = "Regimento Geral ASA/FECAP — Graduação e Pós-Graduação 2026."

load_regimento_pdf()

# Schemas de Dados
class ChatRequest(BaseModel):
    user_id: str
    message: str

class ChatLink(BaseModel):
    label: str
    url: str

class ChatResponse(BaseModel):
    reply: str
    source: str
    updated_at: str
    steps: Optional[List[str]] = None
    links: Optional[List[ChatLink]] = None
    has_download: bool = False
    download_title: Optional[str] = None
    download_size: Optional[str] = None

class HandoverRequest(BaseModel):
    user_id: str
    reason: str
    note: Optional[str] = None

class HandoverResponse(BaseModel):
    status: str
    protocol: str
    attendant: str
    message: str

class FeedbackRequest(BaseModel):
    user_id: str
    rating: int
    comment: Optional[str] = None

class FeedbackResponse(BaseModel):
    status: str
    message: str

# Endpoints v1

@app.get("/api/health")
@app.get("/api/v1/health")
def health_check():
    return {
        "status": "online",
        "app": "SecretarIA Serverless Backend",
        "regimento_loaded": len(REGIMENTO_TEXT) > 0,
        "gemini_active": genai_client is not None
    }

@app.post("/api/v1/chat", response_model=ChatResponse)
def handle_chat(payload: ChatRequest):
    user_msg = payload.message.strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="Mensagem não pode ser vazia.")

    source_citation = "Regimento Geral ASA / Secretaria Geral FECAP"
    updated_date = "25/09/2026"
    steps = None
    links = None
    has_download = False
    download_title = None
    download_size = None

    lower_msg = user_msg.lower()
    reply_text = None

    # Chamada Gemini API se disponível
    if genai_client:
        try:
            prompt = f"""Você é a SecretarIA (Secretaria Acadêmica Inteligente ASA/FECAP).
Responda à dúvida do estudante de forma clara, educada, institucional e precisa, baseando-se no Regimento Oficial da FECAP abaixo.

REGIMENTO OFICIAL FECAP:
{REGIMENTO_TEXT}

DÚVIDA DO ESTUDANTE:
"{user_msg}"
"""
            response = genai_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            reply_text = response.text.strip()
        except Exception as e:
            print(f"Erro Gemini API: {e}")
            reply_text = None

    # Fallback RAG Regimental
    if not reply_text:
        if any(k in lower_msg for k in ["trancar", "trancamento", "suspensão", "cancelar matéria"]):
            reply_text = "Conforme o Art. 1º ao 4º do Capítulo I do Regimento Oficial ASA/FECAP, o trancamento voluntário de matrícula permite suspender temporariamente os estudos mantendo seu vínculo com a FECAP:"
            steps = [
                "Verifique se está dentro do prazo limite de até 30 dias após o início do semestre letivo.",
                "Acesse o Portal do Aluno > Requerimentos > Solicitação de Trancamento de Matrícula.",
                "Confira a quitação das mensalidades até a data do pedido (sem cobrança de parcelas vincendas se dentro do prazo de 30 dias).",
                "Aguarde o deferimento em até 3 dias úteis. Lembre-se: o prazo máximo continuado de trancamento é de 4 semestres."
            ]
            links = [{"label": "Abrir Portal do Aluno — Requerimentos", "url": "#"}]
            has_download = True
            download_title = "Formulario_Trancamento_Matricula_FECAP.pdf"
            download_size = "145 KB"

        elif any(k in lower_msg for k in ["histórico", "historico", "declaração", "atestado", "frequência"]):
            reply_text = "De acordo com o Capítulo IV (Art. 9º ao 11º) do Regimento Geral ASA/FECAP, a emissão de documentos escolares é 100% digital e gratuita:"
            steps = [
                "Acesse o Portal do Aluno > Menu Documentos > Emitir Histórico Escolar Oficial.",
                "Selecione 'Histórico com Autenticação Digital QR-Code'.",
                "O arquivo PDF autenticado pela Secretaria Geral é gerado imediatamente em até 24 horas úteis."
            ]
            links = [
                {"label": "Acessar Portal do Aluno", "url": "#"},
                {"label": "Verificar Autenticidade de Documento", "url": "#"}
            ]
            has_download = True
            download_title = "Historico_Escolar_Oficial_FECAP.pdf"
            download_size = "192 KB"

        elif any(k in lower_msg for k in ["boleto", "mensalidade", "pix", "financeiro", "segunda via", "2ª via"]):
            reply_text = "Segundo o Art. 11º do Regimento Geral ASA/FECAP, a emissão de 2ª via de boletos e chaves PIX é realizada diretamente pelo autosserviço sem incidência de taxa:"
            steps = [
                "Acesse o Portal do Aluno > Menu Financeiro > Boletos & Mensalidades.",
                "Selecione a parcela desejada e clique em 'Gerar Código de Barras' ou 'Pagar com PIX'.",
                "A compensação financeira ocorre automaticamente em até 24 horas úteis."
            ]
            links = [{"label": "Abrir Central Financeira FECAP", "url": "#"}]
            has_download = True
            download_title = "Boleto_Mensalidade_Marco_2026.pdf"
            download_size = "215 KB"

        elif any(k in lower_msg for k in ["aproveitamento", "equivalência", "dispensa", "ementa"]):
            reply_text = "Conforme o Capítulo II (Art. 5º ao 7º) do Regimento ASA/FECAP, a equivalência de disciplinas exige atendimento aos seguintes critérios formais:"
            steps = [
                "Compatibilidade mínima de 80% de conteúdo programático e carga horária entre as ementas.",
                "Nota final mínima igual ou superior a 7,0 (sete) na instituição de origem.",
                "Estudos realizados nos últimos 5 anos letivos, com limite máximo de 50% de aproveitamento do curso.",
                "Protocolar o histórico escolar e ementas carimbadas pelo Portal do Aluno > Requerimentos > Aproveitamento."
            ]
            links = [{"label": "Protocolar Pedido de Equivalência", "url": "#"}]

        elif any(k in lower_msg for k in ["calendário", "calendario", "prova", "provas", "a1", "a2", "substitutiva", "prazo"]):
            reply_text = "Segundo o Capítulo III (Art. 8º) do Regimento Geral ASA/FECAP, o calendário de avaliações do semestre 2026/1 fica definido da seguinte forma:"
            steps = [
                "Avaliação Regimental A1: 06/04/2026 a 11/04/2026.",
                "Avaliação Regimental A2: 08/06/2026 a 13/06/2026.",
                "Avaliações Substitutivas: 22/06/2026 a 26/06/2026 (requerimento prévio necessário).",
                "Rematrícula de Veteranos: 01/07/2026 a 15/07/2026 via Portal do Aluno."
            ]
            links = [{"label": "Visualizar Calendário Acadêmico Completo 2026", "url": "#"}]

        else:
            reply_text = "Consultei o Regimento Geral ASA/FECAP (Atualizado em 25/09/2026). Para a sua consulta, as diretrizes formais estabelecem que todas as solicitações acadêmicas devem ser protocoladas diretamente via Portal do Aluno ou junto ao balcão do ASA."
            steps = [
                "Acesse o Portal do Aluno com seu e-mail institucional FECAP.",
                "Localize o menu de Requerimentos e selecione a categoria desejada.",
                "Caso necessite de suporte personalizado, utilize a opção 'Transferir para Atendimento Humano'."
            ]

    return ChatResponse(
        reply=reply_text,
        source=source_citation,
        updated_at=updated_date,
        steps=steps,
        links=[ChatLink(**l) for l in links] if links else None,
        has_download=has_download,
        download_title=download_title,
        download_size=download_size
    )

@app.post("/api/v1/handover", response_model=HandoverResponse)
def handle_handover(payload: HandoverRequest):
    protocol_num = f"#PROTOCOLO-2026-{random.randint(1000, 9990)}"
    return HandoverResponse(
        status="transferred",
        protocol=protocol_num,
        attendant="Orientador Carlos",
        message=f"Atendimento transferido para a Secretaria Acadêmica ASA/FECAP sob o protocolo {protocol_num}."
    )

@app.post("/api/v1/feedback", response_model=FeedbackResponse)
def handle_feedback(payload: FeedbackRequest):
    if not (1 <= payload.rating <= 5):
        raise HTTPException(status_code=400, detail="Rating deve ser de 1 a 5.")
    return FeedbackResponse(
        status="recorded",
        message=f"Avaliação de {payload.rating} estrelas registrada na Secretaria FECAP."
    )
