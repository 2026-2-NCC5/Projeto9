# Relatório Técnico de Infraestrutura em Nuvem, Docker e Resiliência
**Disciplina:** Sistemas Operacionais e Computação em Nuvem  
**Projeto:** SecretarIA — Assistente Acadêmico Inteligente (FECAP)  
**Etapa:** Entrega Final (Entrega 2 — Versão Revisada e Auditada)  

---

## 1. Introdução
Este relatório consolida a implementação da arquitetura em nuvem, orquestração de contêineres Docker, rotinas de backup, testes reais de desempenho e observabilidade do sistema **SecretarIA**, validado tanto em ambiente de desenvolvimento conteinerizado quanto na máquina virtual Microsoft Azure (`vm-fecap-secretaria`).

---

## 2. Arquitetura de Contêineres, Proxy Reverso e Orquestração

A aplicação é particionada em dois serviços conteinerizados desacoplados e orquestrados via Docker Compose (`docker-compose.yml` no ambiente local e `docker-compose.azure.yml` na VM Azure):

```text
                [ Cliente Web / Navegador ]
                             │
                Porta 80 (HTTP — Sem TLS/443 ativo)
                             ▼
           ┌───────────────────────────────────┐
           │   Contêiner: fecap_guia_frontend  │
           │  - Servidor Nginx (Alpine)        │
           │  - Config: nginx.azure.conf       │
           │  - Assets SPA React compilados    │
           │  - Proxy reverso p/ /api e /health│
           └─────────────────┬─────────────────┘
                             │ Rede interna privada (fecap_azure_net)
                       Porta 8000 (Interna)
                             ▼
           ┌───────────────────────────────────┐
           │   Contêiner: fecap_guia_backend   │
           │  - FastAPI + Uvicorn (Python 3.11)│
           │  - Classificador ML Scikit-learn  │
           │  - Pipeline RAG / ChromaDB        │
           │  - Módulo de Álgebra Linear       │
           └──────────┬────────────────────────┘
                      │ Volumes persistentes (Bind Mounts)
                      ▼
        ┌───────────────────────────┐
        │     Disco do Host / VM    │
        │  - fecap_guia.db (SQLite) │
        │  - chroma_db/ (Vetores)   │
        │  - knowledge_base/ (Docs) │
        │  - backups/ (Snapshots)   │
        └───────────────────────────┘
```

### 2.1 Natureza dos Arquivos de Configuração no Pacote (`05_Configuracoes/`)
Para transparência de auditoria, os arquivos incluídos em `05_Configuracoes/` dividem-se em duas categorias:
1. **Cópias Fiéis da Implantação Executada:**
   - [`Dockerfile.backend`](../05_Configuracoes/Dockerfile.backend): Imagem `python:3.11-slim` com pré-carregamento do modelo `all-MiniLM-L6-v2` e healthcheck em `/health`.
   - [`Dockerfile.frontend`](../05_Configuracoes/Dockerfile.frontend): Multi-stage build (`node:20-alpine` -> `nginx:alpine`) expondo portas HTTP (`5173` e `80`).
   - [`nginx.azure.conf`](../05_Configuracoes/nginx.azure.conf): Configuração real do proxy reverso Nginx na Azure escutando na porta 80 (HTTP), aplicando headers de segurança (`X-Frame-Options`, `X-Content-Type-Options`) e encaminhando `/api/` e `/health` para `http://backend:8000`.
   - [`nginx.conf`](../05_Configuracoes/nginx.conf): Configuração do proxy Nginx para execução local na porta 5173.
2. **Arquivos de Orquestração Sanitizados e Adaptados para Entrega:**
   - [`docker-compose.yml`](../05_Configuracoes/docker-compose.yml) e [`docker-compose.azure.yml`](../05_Configuracoes/docker-compose.azure.yml): Credenciais fixas de exemplo (`POSTGRES_PASSWORD`) foram substituídas por variáveis de ambiente (`${POSTGRES_PASSWORD}`), e a publicação da porta `443` foi desativada/omitida para refletir com exatidão que o ambiente acadêmico opera exclusivamente sob HTTP puro (porta 80), sem certificado TLS/HTTPS ativo.
   - [`backup.sh`](../05_Configuracoes/backup.sh) e [`restore.sh`](../05_Configuracoes/restore.sh): Mantêm a lógica integral executada na VM Azure, acrescidos de resolução dinâmica de diretório raiz (`PROJECT_DIR`) compatível tanto com `deploy/azure/` (2 níveis) quanto com `05_Configuracoes/` (1 nível).

---

## 3. Monitoramento de Recursos Computacionais (CPU e Memória)

A coleta de telemetria dos contêineres foi realizada via utilitário nativo do Docker Engine (`docker stats --no-stream`), conforme registrado em `Ubuntu_evidencias(1).docx` (Capturas 21 a 23) e em `load_test_results.json`:

| Contêiner | CPU (Snapshot Azure) | RAM (Snapshot Azure) | CPU (Antes Carga) | RAM (Antes Carga) | CPU (Após Carga) | RAM (Após Carga) | PIDs |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **fecap_guia_backend** | 0,26% | 436,2 MiB (5,54%) | 0,33% | 412,6 MiB (5,24%) | 0,38% | 425,7 MiB (5,40%) | 29 |
| **fecap_guia_frontend** | 0,00% | 9,125 MiB (0,12%) | 0,00% | 5,836 MiB (0,07%) | 0,00% | 6,105 MiB (0,08%) | 5 |

- **Interpretação Técnica:** O consumo de memória do backend (~412 a 436 MiB de 7,692 GiB totais) reflete o footprint do runtime Python, modelo de embeddings MiniLM em memória e bibliotecas científicas. O frontend Nginx Alpine consome menos de 10 MiB (~0,1% da RAM).

---

## 4. Testes de Carga e Análise de Desempenho (`load_test_results.json`)

Os testes de carga foram executados via script assíncrono real (`run_load_test.py` com `httpx.AsyncClient` e `asyncio.Semaphore`), totalizando **150 requisições reais** distribuídas em **5 cenários** com concorrência máxima de **5 conexões simultâneas**:

| Cenário | Endpoint | Requisições | Concorrência | Tempo Total (s) | Throughput (req/s) | Latência Média (ms) | P50 (ms) | P95 (ms) | P99 (ms) | Sucesso / Erros |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Healthcheck** | `/health` | 50 | 5 | 0,157 s | 317,84 | 14,54 | 10,55 | 32,77 | 36,68 | 100% (0 erros) |
| **2. Perfil Estudante** | `/api/v1/student/profile` | 40 | 5 | 0,756 s | 52,90 | 91,52 | 83,32 | 169,20 | 200,16 | 100% (0 erros) |
| **3. Boletos Pendentes** | `/api/v1/boletos/pending` | 30 | 5 | 6,730 s | 4,46 | 1.052,37 | 711,38 | 3.048,37 | 3.472,26 | 100% (0 erros) |
| **4. RAG Acadêmico (C=2)** | `/api/v1/agent/query` | 10 | 2 | 7,188 s | 1,39 | 1.357,01 | 1.270,83 | 2.330,79 | 2.330,79 | 100% (0 erros) |
| **5. RAG Acadêmico (C=5)** | `/api/v1/agent/query` | 20 | 5 | 13,087 s | 1,53 | 2.992,26 | 2.351,63 | **7.740,53** | 7.740,53 | 100% (0 erros) |

### Análise de Gargalos por Cenário:
- **Endpoints Leves (`/health` e `/api/v1/student/profile`):** Alta vazão (317,84 req/s e 52,90 req/s) e baixa latência (P95 de 32,77 ms e 169,20 ms).
- **Consultas Financeiras (`/api/v1/boletos/pending`):** Latência média de 1.052,37 ms e P95 de 3.048,37 ms sob concorrência 5 devido às leituras relacionais e serialização de boletos.
- **Inferência Vetorial RAG (`/api/v1/agent/query`):** Principal gargalo de CPU. Ao elevar a concorrência de C=2 para C=5, a latência média subiu de 1.357,01 ms para 2.992,26 ms e o P95 atingiu **7.740,53 ms**, refletindo a contenção de CPU durante a vetorização com Sentence-Transformers (`all-MiniLM-L6-v2` em CPU) e busca semântica no ChromaDB.

---

## 5. Procedimentos de Backup, Integridade e Restauração

### 5.1 Script de Backup (`05_Configuracoes/backup.sh`)
- Realiza backup atômico online do SQLite via API nativa (`sqlite3.backup()`), evitando corrupção durante escritas concorrentes.
- Compacta o diretório vetorial `chroma_db` (`chroma_db.tar.gz`) e a base documental `knowledge_base` (`knowledge_base.tar.gz`).
- Calcula hashes SHA-256 (`sha256sums.txt`) e empacota o arquivo final `fecap_guia_backup_20261102T164115Z.tar.gz` (comprovado nas Capturas 25 e 26 de `Ubuntu_evidencias(1).docx`).

### 5.2 Validação Comprovada de Restauração (`03_Evidencias/backup_restore_evidence.json`)
A restauração foi verificada em diretório temporário isolado (sem sobrescrever ou afetar os bancos originais de produção):
1. **Banco Relacional SQLite (`fecap_guia.db`):**
   - `PRAGMA integrity_check`: **`"ok"`** (0 violações de chave estrangeira).
   - Hash SHA-256 do backup e do arquivo restaurado idênticos: `85e89ffa45485b111cad30921d4b36c2f83471d7ad78b47c6d4377fe17578f44` (`hashes_match: true`).
   - Contagem de registros validada: 3 usuários, 30 documentos, 2 estudantes, 105 conversas, 841 logs de auditoria, 216 mensagens, 37 tickets de handoff, 16 feedbacks, 12 validações humanas e 7 boletos.
2. **Base Vetorial ChromaDB (`chroma_db`):**
   - Validada em diretório temporário isolado utilizando o ambiente virtual do projeto (`fecap-guia/.venv/Scripts/python.exe`, `chromadb` versão `1.5.9`).
   - Integridade estrutural do `chroma.sqlite3`: `PRAGMA integrity_check = "ok"`.
   - Hash SHA-256 do snapshot e da cópia restaurada idênticos: `a0187c377409fb7bef4cf8030a5552ff82573fcd96f3d42f625b52f8c9322288` (`hashes_match: true`).
   - Coleção vetorial ativa restaurada com sucesso: **`fecap_knowledge`** contendo **55 chunks/embeddings** íntegros.

---

## 6. Limitações Técnicas e Recomendações de Produção
1. **Ausência de HTTPS/TLS Ativo:** O ambiente na VM Azure operou exclusivamente via HTTP na porta 80 (e porta 8000 em testes diretos). Para produção institucional, elaborou-se o plano técnico de engenharia com Certbot / Let's Encrypt documentado em [`PLANO_IMPLANTACAO_HTTPS_AZURE.md`](../06_Relatorios/PLANO_IMPLANTACAO_HTTPS_AZURE.md).
2. **Estado da VM Azure:** A VM `vm-fecap-secretaria` (`191.233.19.182`) encontra-se atualmente desalocada/desligada para preservação de créditos acadêmicos, tendo todas as suas execuções documentadas nas 27 capturas de `Ubuntu_evidencias(1).docx`.
3. **Logs HTTP Estruturados em JSON:** Requisito 100% implementado e validado via middleware no FastAPI, com evidências completas e testes empíricos em [`RELATORIO_VALIDACAO_LOGS_HTTP_JSON.md`](../06_Relatorios/RELATORIO_VALIDACAO_LOGS_HTTP_JSON.md).
