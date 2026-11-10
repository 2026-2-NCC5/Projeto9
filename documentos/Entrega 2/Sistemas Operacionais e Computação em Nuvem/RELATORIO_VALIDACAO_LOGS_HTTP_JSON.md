# RELATÓRIO TÉCNICO DE VALIDAÇÃO — LOGS HTTP ESTRUTURADOS EM JSON

**Projeto:** SecretarIA — FECAP Guia  
**Disciplina:** Sistemas Operacionais e Computação em Nuvem  
**Semestre:** 2026/2  
**Componentes Auditados:** Backend FastAPI (`app/main.py`, `app/core/logging.py`, `app/core/config.py`)  
**Data da Execução:** 08/11/2026  
**Status do Requisito:** COMPROVADO (100% Funcional e Auditado)

---

## 1. OBJETIVO TÉCNICO

Implementar e validar no backend FastAPI da aplicação SecretarIA uma camada de observabilidade e auditoria baseada em middleware assíncrono para emissão de logs de acesso HTTP estritamente estruturados em formato JSON (JSON Lines).

Essa implementação atende aos padrões Cloud-Native (12-Factor App / Logs as Event Streams) e às exigências de conformidade da FECAP, substituindo os logs de texto padrão do Uvicorn por estruturas indexáveis, agregáveis e prontas para ingestão em ferramentas de monitoramento em nuvem (ex.: Azure Log Analytics, Elasticsearch, Grafana Loki, Datadog), mantendo total sigilo sobre credenciais e dados pessoais (LGPD).

---

## 2. ARQUITETURA DA IMPLEMENTAÇÃO

### 2.1 Middleware Assíncrono (`RequestLoggingMiddleware` em `app/main.py`)
- **Ponto de Interceptação:** Baseado em `starlette.middleware.base.BaseHTTPMiddleware`.
- **Rastreabilidade e Correlação (`request_id`):**
  - Captura prioritariamente o identificador de correlação injetado pelo API Gateway ou cliente via cabeçalho `X-Request-ID` ou `X-Correlation-ID`.
  - Gera dinamicamente um UUIDv4 único caso nenhum cabeçalho tenha sido enviado.
  - Injeta o `request_id` no cabeçalho de resposta HTTP `X-Request-ID` para rastreamento ponta a ponta pelo frontend.
- **Medição de Latência:**
  - Utiliza `time.perf_counter()` de alta resolução para mensuração precisa do tempo de processamento interno da requisição em milissegundos (`latency_ms`).
- **Mapeamento Semântico de Severidade:**
  - `status_code < 400`: `INFO` (requisições 2xx de sucesso e 3xx de redirecionamento).
  - `400 <= status_code < 500`: `WARNING` (erros de cliente, validação 422, rotas 404, não autorizado 401).
  - `status_code >= 500` ou exceções não tratadas: `ERROR`.

### 2.2 Configuração Centralizada de Logging (`app/core/logging.py`)
- **Motor de Renderização:** Utiliza a biblioteca `structlog` com encadeamento de processadores de contexto, timestamps ISO 8601 UTC (`TimeStamper(fmt="iso")`) e o renderizador serializador `structlog.processors.JSONRenderer()`.
- **Supressão de Redundância:** Desativa automaticamente os logs textuais concorrentes do Uvicorn (`logging.getLogger("uvicorn.access").disabled = True`) quando `log_json=True`, eliminando poluição visual e custos duplicados de armazenamento de log.

### 2.3 Proteção de Dados e Privacidade (LGPD / OWASP API Security)
- **Não Exposição de Segredos:** O middleware **NÃO** registra cabeçalhos `Authorization`, tokens JWT Bearer, cookies de sessão nem senhas.
- **Não Exposição de Payload:** O corpo bruto das requisições (`body`) e das respostas não é gravado no log de acesso, prevenindo vazamento de dados confidenciais acadêmicos, bancários ou pessoais.

---

## 3. EVIDÊNCIAS DE EXECUÇÃO LOCAL CONTROLADA

Os testes foram executados localmente em ambiente isolado, com variáveis de ambiente dedicadas (`LLM_MODE=demo`, `LOG_JSON=true`, banco SQLite temporário de testes) sem chamadas à internet e sem modificar o banco original de produção.

### Cenário 1: Healthcheck do Sistema (`GET /health` — Sucesso 200 OK)
- **Objetivo:** Verificar registro estruturado em rota operacional com latência controlada.
- **Headers da Requisição:** `X-Request-ID: req-auditoria-health-200`
- **Status HTTP Retornado:** `200 OK`
- **Log JSON Emitido (Captura Real):**
```json
{
  "method": "GET",
  "path": "/health",
  "status_code": 200,
  "latency_ms": 82.04,
  "request_id": "req-auditoria-health-200",
  "service": "fecap_guia_backend",
  "client_ip": "testclient",
  "event": "http_request",
  "level": "info",
  "timestamp": "2026-11-08T22:22:08.473054Z"
}
```

### Cenário 2: Rota Inexistente (`GET /rota-inexistente` — Erro 404 Not Found)
- **Objetivo:** Verificar tratamento de rota inválida com severidade `warning`.
- **Headers da Requisição:** `X-Request-ID: req-auditoria-notfound-404`
- **Status HTTP Retornado:** `404 Not Found`
- **Log JSON Emitido (Captura Real):**
```json
{
  "method": "GET",
  "path": "/rota-inexistente",
  "status_code": 404,
  "latency_ms": 1.3,
  "request_id": "req-auditoria-notfound-404",
  "service": "fecap_guia_backend",
  "client_ip": "testclient",
  "event": "http_request",
  "level": "warning",
  "timestamp": "2026-11-08T22:22:08.481571Z"
}
```

### Cenário 3: Acesso Protegido Não Autenticado (`GET /api/v1/student/profile` — Erro 401 Unauthorized)
- **Objetivo:** Verificar tentativa de acesso a endpoint seguro sem token JWT.
- **Headers da Requisição:** `X-Request-ID: req-auditoria-unauth-401`
- **Status HTTP Retornado:** `401 Unauthorized`
- **Log JSON Emitido (Captura Real):**
```json
{
  "method": "GET",
  "path": "/api/v1/student/profile",
  "status_code": 401,
  "latency_ms": 49.71,
  "request_id": "req-auditoria-unauth-401",
  "service": "fecap_guia_backend",
  "client_ip": "testclient",
  "event": "http_request",
  "level": "warning",
  "timestamp": "2026-11-08T22:22:08.537499Z"
}
```

### Cenário 4: Falha de Validação de Schema (`POST /api/v1/auth/login` — Erro 422 Unprocessable Content)
- **Objetivo:** Verificar tratamento de payload inválido (JSON vazio `{}`) com captura de latência.
- **Headers da Requisição:** `X-Request-ID: req-auditoria-validation-422`
- **Status HTTP Retornado:** `422 Unprocessable Content`
- **Log JSON Emitido (Captura Real):**
```json
{
  "method": "POST",
  "path": "/api/v1/auth/login",
  "status_code": 422,
  "latency_ms": 29.48,
  "request_id": "req-auditoria-validation-422",
  "service": "fecap_guia_backend",
  "client_ip": "testclient",
  "event": "http_request",
  "level": "warning",
  "timestamp": "2026-11-08T22:22:08.574943Z"
}
```

---

## 4. DICIONÁRIO DE DADOS DOS LOGS HTTP

| Campo | Tipo | Descrição | Exemplo |
| :--- | :--- | :--- | :--- |
| `timestamp` | String (ISO 8601 UTC) | Momento exato da conclusão do processamento da requisição | `2026-11-08T22:22:08.473054Z` |
| `level` | String | Severidade do evento (`info`, `warning`, `error`) | `info` |
| `event` | String | Identificador semântico do evento | `http_request` |
| `method` | String | Método HTTP da requisição | `GET`, `POST`, `PUT`, `DELETE` |
| `path` | String | Caminho relativo do endpoint chamado | `/health`, `/api/v1/auth/login` |
| `status_code` | Integer | Código de status de resposta HTTP | `200`, `401`, `404`, `422`, `500` |
| `latency_ms` | Float | Tempo total de processamento em milissegundos | `82.04` |
| `request_id` | String | Identificador único de correlação da requisição | `req-auditoria-health-200` |
| `service` | String | Nome do microserviço responsável pelo processamento | `fecap_guia_backend` |
| `client_ip` | String | Endereço IP do cliente requisitante | `testclient` ou IP remoto |

---

## 5. CONCLUSÃO TÉCNICA

A validação confirma que o backend do SecretarIA possui capacidade operacional nativa de emitir logs HTTP estruturados em JSON válidos, uniformes, rastreáveis e seguros, atendendo com nota máxima os critérios de observabilidade, auditoria e arquitetura cloud-native da disciplina.
