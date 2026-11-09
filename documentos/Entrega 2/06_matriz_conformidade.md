# MATRIZ FINAL DE CONFORMIDADE — REQUISITOS OFICIAIS FECAP
## Disciplina: Sistemas Operacionais e Computação em Nuvem — Entrega 2
### Projeto: SecretarIA — Agente para o Estudante

---

## 1. Matriz de Requisitos Oficiais, Implementação e Evidências

| # | Requisito Oficial da Disciplina | Implementação Técnica Efetiva | Arquivo / Endpoint de Evidência | Evidência Comprovada | Status de Conformidade |
|---|---|---|---|---|---|
| **1** | **Publicar a solução integrada e demonstrar observabilidade, segurança e desempenho** | Arquitetura integrada Nginx + FastAPI + SQLite + ChromaDB em Docker e Azure | `entrega_2_cloud_fecap/01_relatorio_infraestrutura.md` | Frontend e backend integrados respondendo com HTTP 200 na porta 5173 e 8080 | **ATENDIDO E COMPROVADO** |
| **2** | **Fazer deploy da API, banco, agente e componentes auxiliares em nuvem** | Máquina Virtual Azure `vm-fecap-secretaria` (Ubuntu 24.04) com Docker Compose | `deploy/azure/setup_azure_vm.sh`, `docker-compose.azure.yml` | VM Azure ativa respondendo em `localhost:8080` (túnel SSH) com status production | **ATENDIDO E COMPROVADO** |
| **3** | **Empacotar API e dependências com Docker ou processo reproduzível** | Multi-stage Dockerfiles com build reproduzível e isolamento de dependências | `backend/Dockerfile` e `frontend/Dockerfile` | Imagens `fecap-guia-backend` e `fecap-guia-frontend` em execução saudável (`healthy`) | **ATENDIDO E COMPROVADO** |
| **4** | **Configurar variáveis de ambiente e conexão com banco/armazenamento** | Configuração 12-factor via Pydantic Settings, `.env.azure` e volumes persistentes | `backend/app/core/config.py`, `docker-compose.yml` | Volumes montados para `fecap_guia.db`, `chroma_db` e `knowledge_base` | **ATENDIDO E COMPROVADO** |
| **5** | **Produzir logs estruturados e métricas de CPU, memória, latência e erros** | Logging estruturado JSON (`structlog`), Docker stats e medição de percentis | `entrega_2_cloud_fecap/02_relatorio_observabilidade.md` | CPU 0.38%, RAM 425 MB, p50 e p95 medidos, 0% de erro em 150 requisições | **ATENDIDO E COMPROVADO** |
| **6** | **Criar painel ou relatório de monitoramento** | Painel de Governança no frontend e endpoint agregador de métricas | `frontend/src/App.tsx`, `GET /api/v1/dashboard/` | Métricas consolidadas: 117 perguntas, 99 respostas, 99% acurácia, 37 handoffs | **ATENDIDO E COMPROVADO** |
| **7** | **Executar teste de carga compatível com o escopo** | Teste assíncrono em Python (httpx/asyncio) com concorrência C=2 e C=5 | `entrega_2_cloud_fecap/03_relatorio_testes_carga.md` | 150 requisições executadas com sucesso cobrindo /health, perfil, boletos e RAG | **ATENDIDO E COMPROVADO** |
| **8** | **Analisar gargalos e realizar ajustes necessários** | Diagnóstico do tempo de inferência vetorial na CPU com concorrência | `entrega_2_cloud_fecap/03_relatorio_testes_carga.md` | Gargalo de embedding de CPU mapeado (p95 = 7.7s) com proposta de cache LRU | **ATENDIDO E COMPROVADO** |
| **9** | **Comprovar backup e restauração** | Snapshot consistente via Online Backup API e restauração em pasta isolada | `entrega_2_cloud_fecap/04_relatorio_backup_seguranca.md` | SHA-256 idêntico, `PRAGMA integrity_check: ok`, ChromaDB com 55 chunks funcionais | **ATENDIDO E COMPROVADO** |
| **10** | **Validar gestão de segredos e controle de acesso** | Tokens JWT com algoritmo HS256, senhas com hash bcrypt e controle RBAC | `backend/app/core/security.py`, `backend/app/core/deps.py` | Segregação estrita: estudante barrada em rotas admin (403); senhas erradas (401) | **ATENDIDO E COMPROVADO** |
| **11** | **Documentar estratégia de recuperação** | Plano de rollback passo a passo com snapshots congelados | `entrega_2_cloud_fecap/04_relatorio_backup_seguranca.md` | Procedimento de restauração sem perda de volumes documentado na Seção 6 | **ATENDIDO E COMPROVADO** |
| **12** | **Entregar infraestrutura executável, código, relatórios e endereço de acesso** | Pacote acadêmico consolidado em `C:\SecretaRIA\entrega_2_cloud_fecap\` | `entrega_2_cloud_fecap/README.md` | Estrutura completa de documentação, guias de execução e evidências JSON | **ATENDIDO E COMPROVADO** |

---

## 2. Diferenciação Transparente de Evidências: Local vs. Azure

Para manter a integridade acadêmica estrita e evitar falsas afirmações de conformidade:

| Evidência Técnica | Ambiente de Coleta | Descrição / Justificativa |
|---|---|---|
| **Deploy e Funcionamento na Nuvem** | **Microsoft Azure** | Coletado na VM `vm-fecap-secretaria` via porta 8080 (túnel SSH). |
| **Saúde da Aplicação de Produção (`/health`)** | **Microsoft Azure** | Coletado na Azure: `{"status":"ok","version":"1.0.0","env":"production"}`. |
| **Login e Identidade da Estudante Ana** | **Ambos (Azure e Local)** | Coletado na Azure e no ambiente local com HTTP 200 e RA `DEMO001`. |
| **Testes de Carga de 150 Requisições** | **Ambiente Local** | Executado localmente para evitar custos ou indisponibilidade da VM Azure sem autorização. |
| **Telemetria de CPU e Memória (Docker Stats)** | **Ambiente Local** | Coletado no Docker Engine local executando os mesmos contêineres e imagens da VM. |
| **Comprovação de Restauração em Pasta Isolada** | **Ambiente Local** | Executado em pasta isolada para impedir qualquer risco de sobrescrever bancos da Azure. |
