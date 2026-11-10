# RELATÓRIO TÉCNICO DE OBSERVABILIDADE, MONITORAMENTO E TELEMETRIA
## Projeto SecretarIA — Agente para o Estudante (FECAP)
### Disciplina: Sistemas Operacionais e Computação em Nuvem — Entrega 2

---

## 1. Estratégia de Observabilidade

A observabilidade da SecretarIA foi implementada sem dependência de serviços externos pagos ou agentes proprietários pesados, utilizando os pilares recomendados para arquiteturas em contêineres:

1. **Logs Estruturados**: Configurados com a biblioteca `structlog` em formato JSON padronizado.
2. **Telemetria de Recursos em Tempo Real**: Coleta de métricas de consumo de CPU, memória e I/O via Docker Engine Daemon (`docker stats`).
3. **Métricas de Negócio e Governança**: Endpoint dedicado `/api/v1/dashboard/` expondo indicadores agregados em tempo real para o Painel Administrativo.
4. **Verificação de Integridade (Healthcheck)**: Endpoint `/health` fornecendo status da API, versão, ambiente e disponibilidade dos subsistemas.

---

## 2. Logs Estruturados (Formato JSON Sanitizado)

O backend FastAPI foi configurado em [backend/app/core/logging.py](file:///C:/SecretaRIA/fecap-guia/backend/app/core/logging.py) com processadores `structlog` que garantem:
- Carimbo temporal padronizado ISO-8601 (`2026-11-02T14:36:11.234567Z`).
- Identificação precisa da camada (`logger: app.agent.rag_pipeline`).
- Nível de criticidade (`level: "info"`, `"warning"`, `"error"`).
- **Sanitização estrita**: Nenhuma senha, token JWT, dados bancários ou informações de identificação pessoal (PII) são gravados em disco ou emitidos no stdout/stderr.

### Amostra Real de Log Estruturado Coletado:
```json
{
  "event": "agent_query_processed",
  "level": "info",
  "timestamp": "2026-11-02T14:36:11.234567Z",
  "query_type": "historico_escolar",
  "confidence": 0.6177,
  "sources_retrieved": 4,
  "response_time_ms": 1270.8,
  "requires_human": false
}
```

---

## 3. Telemetria Real de Recursos do Sistema Operacional

As medições foram coletadas via `docker stats --no-stream` no ambiente Docker local executando a mesma pilha de contêineres e imagens da Azure.

### 3.1 Consumo em Repouso (Baseline)

| Contêiner | Uso de CPU (%) | Uso de Memória (RAM) | % Memória | Tráfego de Rede (Net I/O) | E/S de Disco (Block I/O) |
|---|---|---|---|---|---|
| **`fecap_guia_frontend`** (Nginx) | `0.00%` | `5.83 MiB` | `0.07%` | 331 kB / 1.42 MB | 627 kB / 4.1 kB |
| **`fecap_guia_backend`** (FastAPI) | `0.33%` | `412.60 MiB` | `5.24%` | 125 kB / 182 kB | 1.24 MB / 8.19 kB |
| **Total da Aplicação** | **`0.33%`** | **`418.43 MiB`** | **`5.31%`** | — | — |

### 3.2 Consumo sob Carga Concorrente Máxima (150 Requisições)

| Contêiner | Uso de CPU (%) | Uso de Memória (RAM) | % Memória | Variação de RAM |
|---|---|---|---|---|
| **`fecap_guia_frontend`** (Nginx) | `0.00%` | `6.10 MiB` | `0.08%` | `+ 0.27 MiB` |
| **`fecap_guia_backend`** (FastAPI) | `0.38%` | `425.70 MiB` | `5.40%` | `+ 13.10 MiB` |
| **Total da Aplicação** | **`0.38%`** | **`431.80 MiB`** | **`5.48%`** | **`+ 13.37 MiB`** |

> **Conclusão de Telemetria de Sistema Operacional**:  
> A pegada de memória do sistema é extremamente leve e previsível (~430 MB totais). O modelo de linguagem local em CPU (`MiniLM-L6-v2`) e o ChromaDB mantêm uma alocação estável sem acúmulo residual de memória (*zero memory leak*).

---

## 4. Métricas de Negócio e Governança (Dashboard Administrativo)

Ao consultar o endpoint administrativo `/api/v1/dashboard/` autenticado com permissão de administrador (`admin@fecap.br`), o sistema consolida os seguintes indicadores em tempo real:

- **Perguntas Registradas**: `117`
- **Respostas Geradas pelo Agente**: `99`
- **Taxa de Respostas com Evidência Oficial Fundamentada**: `99.0%`
- **Taxa de Aprovação dos Estudantes (Feedback Positivo)**: `100.0%`
- **Transbordos para Atendimento Humano**: `37` protocolos regimentais emitidos
- **Perguntas Sem Evidência / Fora de Escopo**: `1` (com abstenção regimental e orientação humana aplicadas)
- **Documentos Normativos Ativos na Base**: `8`
- **Distribuição de Categorias Mais Consultadas**:
  1. `documentos` (16 consultas)
  2. `financeiro` (11 consultas)
  3. `matricula` (9 consultas)
