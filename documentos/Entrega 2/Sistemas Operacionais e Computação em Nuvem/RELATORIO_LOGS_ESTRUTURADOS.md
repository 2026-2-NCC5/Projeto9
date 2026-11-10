# Relatório Técnico de Logs Estruturados e Observabilidade
**Projeto:** SecretarIA — Assistente Acadêmico Inteligente (FECAP Guia)  
**Disciplina:** Sistemas Operacionais e Computação em Nuvem  
**Semestre Letivo:** 2026/2  
**Data:** 08/11/2026  
**Auditor:** Equipe de Engenharia e Auditoria de Software  

---

## 1. Objetivo da Auditoria de Logs
Inspecionar a configuração e a emissão de logs do backend FastAPI do SecretarIA, avaliando o grau de estruturação dos eventos, rastreabilidade, segurança da informação (sanitização de dados sensíveis e conformidade LGPD) e aderência aos padrões de observabilidade em contêineres e sistemas operacionais.

---

## 2. Diagnóstico da Configuração Atual

A configuração de logging da aplicação foi inspecionada diretamente no módulo [`app/core/logging.py`](../../fecap-guia/backend/app/core/logging.py):

```python
def configure_logging():
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer() if settings.debug
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(level=log_level)
```

### Análise dos 7 Critérios Obrigatórios:

| Critério de Log | Status no Backend | Mecanismo Identificado |
| :--- | :---: | :--- |
| **1. Timestamp** | **ATENDIDO** | Formato ISO-8601 UTC via `structlog.processors.TimeStamper(fmt="iso")`. |
| **2. Nível do Evento (INFO, WARNING, ERROR)** | **ATENDIDO** | Atribuído por `structlog.processors.add_log_level`. |
| **3. Serviço / Componente Emissor** | **ATENDIDO** | Injetado pelo identificador do módulo (`logger = get_logger(__name__)`). |
| **4. Método e Rota HTTP** | **PARCIAL** | Emitido pelo servidor ASGI Uvicorn em formato de texto padrão (`INFO: 127.0.0.1 - "GET /health HTTP/1.1" 200 OK`), mas não unificado no JSON do `structlog`. |
| **5. Código de Resposta HTTP** | **PARCIAL** | Presente no log de acesso do Uvicorn e nos handlers de exceção, mas ausente do envelope estruturado do `structlog` nas rotas de negócio. |
| **6. Latência da Requisição** | **PARCIAL** | Calculada internamente no pipeline RAG (`app/agent/rag_pipeline.py`) e nos testes de carga (`run_load_test.py`), mas sem middleware HTTP global registrando `latency_ms` para todas as rotas. |
| **7. Identificador de Correlação** | **PARCIAL** | Implementado no pipeline RAG como `run_id = str(uuid.uuid4())`, propagado em todas as etapas de busca vetorial e abstenção, mas sem middleware injetando `X-Correlation-ID` global no ciclo de vida HTTP. |

---

## 3. Exemplos Reais e Anonimizados de Logs Coletados

### 3.1 Inicialização do Backend (Formato JSON Estruturado — `structlog`)
```json
{
  "event": "Iniciando FECAP Guia",
  "level": "info",
  "timestamp": "2026-11-02T14:30:00.104218Z",
  "version": "1.0.0",
  "mode": "demo"
}
```

### 3.2 Execução do Pipeline RAG com Correlation ID (`run_id`)
```json
{
  "event": "RAG pipeline iniciado",
  "level": "info",
  "timestamp": "2026-11-02T14:36:11.234567Z",
  "logger": "app.agent.rag_pipeline",
  "run_id": "899b2238-caef-487b-83d2-6e1ea476a9c0",
  "student_id": "student-anon-001",
  "question_len": 42
}
```

```json
{
  "event": "Chunks recuperados",
  "level": "info",
  "timestamp": "2026-11-02T14:36:11.890123Z",
  "logger": "app.agent.rag_pipeline",
  "run_id": "899b2238-caef-487b-83d2-6e1ea476a9c0",
  "total_raw": 4,
  "top_k": 4
}
```

```json
{
  "event": "RAG pipeline concluido",
  "level": "info",
  "timestamp": "2026-11-02T14:36:12.591577Z",
  "logger": "app.agent.rag_pipeline",
  "run_id": "899b2238-caef-487b-83d2-6e1ea476a9c0"
}
```

### 3.3 Log de Borda Docker / Uvicorn (Saída Padrão do Contêiner)
```text
INFO:     172.16.0.1:48210 - "POST /api/v1/agent/query HTTP/1.1" 200 OK
INFO:     172.16.0.1:48214 - "GET /health HTTP/1.1" 200 OK
```

### 3.4 Encapsulamento pelo Driver Docker (`json-file` na Azure)
Na VM Azure, o daemon Docker encapsula as linhas emitidas no stdout em envelopes JSON:
```json
{
  "log": "{\"event\": \"RAG pipeline concluido\", \"level\": \"info\", \"timestamp\": \"2026-11-02T14:36:12.591577Z\", \"run_id\": \"899b2238-caef-487b-83d2-6e1ea476a9c0\"}\n",
  "stream": "stdout",
  "time": "2026-11-02T14:36:12.592001429Z"
}
```

---

## 4. Política de Sanitização e Proteção de Dados (LGPD)

A inspeção do código comprovou que a aplicação segue boas práticas estritas de privacidade:
1. **Senhas e Hashes:** Nenhuma senha em texto puro ou hash bcrypt é emitida em logs de autenticação. O router [`app/api/v1/auth.py`](../../fecap-guia/backend/app/api/v1/auth.py) registra apenas `action="login_failed"` ou `action="login_success"`.
2. **Tokens JWT:** Os cabeçalhos `Authorization: Bearer <token>` e segredos de assinatura não são logados.
3. **Conteúdo de Conversas:** O pipeline RAG registra apenas `question_len=len(question)` e métricas de pontuação, sem gravar o texto integral das perguntas ou respostas nos arquivos de log.
4. **Trilhas de Auditoria:** Eventos de negócio são gravados na tabela relacional `audit_logs` (841 registros validados no snapshot), permitindo conformidade regulatória sem poluir os logs de infraestrutura com dados sensíveis.

---

## 5. Pendência Técnica Identificada e Proposta de Implementação Mínima

### Pendência:
Embora o processamento do agente utilize `structlog` com `run_id`, as requisições HTTP genéricas não passam por um middleware centralizado que unifique `correlation_id`, `http_method`, `route`, `status_code` e `latency_ms` em um único registro JSON estruturado para cada chamada.

### Proposta Técnica de Melhoria (Sem Execução Automática):
Recomenda-se adicionar um middleware ASGI leve em [`app/main.py`](../../fecap-guia/backend/app/main.py):

```python
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        start_time = time.perf_counter()
        
        response = await call_next(request)
        
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(
            "http_request_finished",
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            latency_ms=latency_ms,
            client_ip=request.client.host if request.client else None,
        )
        response.headers["X-Correlation-ID"] = correlation_id
        return response
```

> **Decisão de Preservação:** Em estrito cumprimento às regras operacionais, esta melhoria está **documentada como recomendação técnica para o ciclo de produção**, não tendo sido aplicada de forma não autorizada no código de produção.
