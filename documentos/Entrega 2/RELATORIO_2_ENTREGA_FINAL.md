# Relatório Acadêmico 2 — Entrega Final (Nuvem, Orquestração e Resiliência)
**Instituição:** Fundação Escola de Comércio Álvares Penteado (FECAP)  
**Curso:** Ciência da Computação / Sistemas de Informação  
**Disciplina:** Sistemas Operacionais e Computação em Nuvem  
**Projeto:** SecretarIA — Assistente Acadêmico Inteligente  
**Autor:** Equipe de Desenvolvimento SecretarIA  
**Data:** 08/11/2026 (Versão Final Auditada)

---

## 1. Introdução
A computação em nuvem permite o provisionamento controlado sob demanda de poder computacional, isolamento de recursos e tolerância a falhas. Este relatório documenta a entrega final da infraestrutura do **SecretarIA**, contemplando a orquestração em contêineres Docker, a implantação na nuvem Microsoft Azure (VM Ubuntu Server 24.04.5 LTS), observabilidade de recursos via telemetria, resultados reais do teste de carga (150 requisições em 5 cenários) e validação completa de backup e restauração isolada (SQLite e ChromaDB).

---

## 2. Objetivos da Infraestrutura
- Orquestrar serviços desacoplados (Frontend Nginx/React e Backend FastAPI/SQLite/ChromaDB) com Docker Compose e rede interna isolada.
- Monitorar o consumo de CPU e memória RAM dos contêineres em repouso e sob carga.
- Executar testes de carga distribuídos nos endpoints da API, documentando latência média, percentis (P50, P95, P99), vazão e gargalos computacionais.
- Implementar e validar rotinas atômicas de backup e restauração em ambiente isolado com validação de hash criptográfico SHA-256, teste estrutural `PRAGMA integrity_check` e inspeção das coleções vetoriais do ChromaDB.
- Documentar regras de rede, controle de portas e políticas de segurança aplicadas no Network Security Group (NSG) da Azure.

---

## 3. Arquitetura em Nuvem, Contêineres e Configurações

### 3.1 Ambiente de Nuvem (Microsoft Azure)
- **Máquina Virtual:** `vm-fecap-secretaria` (Standard_B2s: 2 vCPUs, 8 GiB RAM).
- **Sistema Operacional:** Ubuntu Server 24.04.5 LTS (Kernel Linux 7.0.0-1017-azure x86_64).
- **Rede e Acesso:** IP público `191.233.19.182`, FQDN `vm-fecap-secretaria.brazilsouth.cloudapp.azure.com`.
- **Controle de Portas (NSG) e Protocolo HTTP:** Entrada restrita às portas 22 (SSH exclusivamente com chave RSA 4096 / `chmod 600`), 80 (HTTP) e 8000 (FastAPI). O ambiente acadêmico opera exclusivamente em **HTTP puro (porta 80)**; não há certificado TLS/HTTPS configurado e, por rigor técnico, a porta 443 não é publicada como operacional.

> [!NOTE]
> **Status Atual da VM na Azure:** A VM foi provisionada, testada e validada na Azure (Capturas 16 a 27 de `Ubuntu_evidencias(1).docx`). Para evitar consumo contínuo de créditos estudantis fora das janelas de avaliação, a instância encontra-se atualmente desalocada/desligada.

### 3.2 Distinção entre Cópias Fiéis e Configurações Sanitizadas (`05_Configuracoes/`)
- **Cópias Fiéis da Implantação:** `Dockerfile.backend`, `Dockerfile.frontend`, `nginx.azure.conf` (proxy reverso HTTP na porta 80 para a Azure) e `nginx.conf` (proxy local na porta 5173).
- **Configurações Sanitizadas e Adaptadas:** `docker-compose.yml` e `docker-compose.azure.yml` tiveram senhas fixas de exemplo substituídas por variáveis de ambiente (`${POSTGRES_PASSWORD}`) e a porta `443` removida/comentada para refletir a ausência de TLS. Os scripts `backup.sh` e `restore.sh` receberam resolução automática de caminho relativo (`PROJECT_DIR`) compatível tanto com `deploy/azure/` (`../..`) quanto com `05_Configuracoes/` (`..`).

---

## 4. Telemetria e Monitoramento de Recursos

Com base no utilitário `docker stats --no-stream` (registrado em `load_test_results.json` e nas Capturas 21 a 23 de `Ubuntu_evidencias(1).docx`):

| Contêiner | CPU (Snapshot Azure) | RAM (Snapshot Azure) | CPU (Antes Carga) | RAM (Antes Carga) | CPU (Após Carga) | RAM (Após Carga) | PIDs |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **fecap_guia_backend** | 0,26% | 436,2 MiB (5,54%) | 0,33% | 412,6 MiB (5,24%) | 0,38% | 425,7 MiB (5,40%) | 29 |
| **fecap_guia_frontend** | 0,00% | 9,125 MiB (0,12%) | 0,00% | 5,836 MiB (0,07%) | 0,00% | 6,105 MiB (0,08%) | 5 |

---

## 5. Resultados Reais do Teste de Carga (`load_test_results.json`)

O teste de carga automatizado (`run_load_test.py`) executou **150 requisições reais** distribuídas em **5 cenários**, com concorrência máxima de **5 conexões simultâneas**:

| Cenário de Teste | Endpoint | Req. | Concorrência | Taxa Sucesso | Throughput | Latência Média | P50 (Mediana) | P95 | P99 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Healthcheck** | `/health` | 50 | 5 | **100%** (50/50) | 317,84 req/s | 14,54 ms | 10,55 ms | 32,77 ms | 36,68 ms |
| **2. Perfil Estudante** | `/api/v1/student/profile` | 40 | 5 | **100%** (40/40) | 52,90 req/s | 91,52 ms | 83,32 ms | 169,20 ms | 200,16 ms |
| **3. Boletos Pendentes** | `/api/v1/boletos/pending` | 30 | 5 | **100%** (30/30) | 4,46 req/s | 1.052,37 ms | 711,38 ms | 3.048,37 ms | 3.472,26 ms |
| **4. RAG Acadêmico (C=2)**| `/api/v1/agent/query` | 10 | 2 | **100%** (10/10) | 1,39 req/s | 1.357,01 ms | 1.270,83 ms | 2.330,79 ms | 2.330,79 ms |
| **5. RAG Acadêmico (C=5)**| `/api/v1/agent/query` | 20 | 5 | **100%** (20/20) | 1,53 req/s | 2.992,26 ms | 2.351,63 ms | **7.740,53 ms** | 7.740,53 ms |

### Análise Crítica dos Gargalos:
- **Rotas Leves (`/health` e `/api/v1/student/profile`):** Latência média de 14,54 ms e 91,52 ms, sem gargalo.
- **Consulta de Boletos (`/api/v1/boletos/pending`):** Latência média de 1.052,37 ms (P95 de 3.048,37 ms) sob concorrência 5.
- **Motor RAG (`/api/v1/agent/query`):** Sob concorrência 5, o P95 atingiu **7.740,53 ms (7,74s)** devido ao uso intensivo de CPU pelo modelo de embeddings `all-MiniLM-L6-v2` e busca vetorial concorrente.

---

## 6. Backup e Validação de Restauração em Ambiente Isolado

### 6.1 Execução do Backup Consistente
O script [`backup.sh`](../05_Configuracoes/backup.sh) gerou na VM Azure o pacote `fecap_guia_backup_20261102T164115Z.tar.gz` (Capturas 25 a 27 de `Ubuntu_evidencias(1).docx`), contendo snapshot online do SQLite (`sqlite3.backup()`), `chroma_db.tar.gz`, `knowledge_base.tar.gz` e manifesto `sha256sums.txt`.

### 6.2 Validação Comprovada da Restauração (`backup_restore_evidence.json`)
Tanto o banco SQLite quanto a base vetorial ChromaDB foram restaurados e validados em diretório temporário isolado, preservando intactos os arquivos de produção:
1. **SQLite (`fecap_guia.db`):**
   - Hash SHA-256 idêntico entre backup e restaurado: `85e89ffa45485b111cad30921d4b36c2f83471d7ad78b47c6d4377fe17578f44` (`hashes_match: true`).
   - `PRAGMA integrity_check = "ok"` e `foreign_key_violations = 0`.
   - Tabelas verificadas: `users` (3), `knowledge_documents` (30), `students` (2), `conversations` (105), `audit_logs` (841), `messages` (216), `handoff_tickets` (37), `feedbacks` (16), `human_validations` (12), `boletos` (7).
2. **ChromaDB (`chroma_db`):**
   - Validado em diretório temporário isolado com o ambiente virtual Python do projeto (`chromadb 1.5.9`).
   - Hash SHA-256 do `chroma.sqlite3` idêntico entre snapshot e restaurado: `a0187c377409fb7bef4cf8030a5552ff82573fcd96f3d42f625b52f8c9322288` (`hashes_match: true`).
   - `PRAGMA integrity_check = "ok"`.
   - Coleção vetorial inspecionada via `chromadb.PersistentClient`: **`fecap_knowledge`** ativa e íntegra com **55 chunks/embeddings**.

---

## 7. Limitações Técnicas Conhecidas
1. **Protocolo HTTP (Sem HTTPS/TLS):** O ambiente acadêmico opera sobre HTTP na porta 80. Para produção institucional, requer-se configuração de certificado TLS (Let's Encrypt / Certbot) na porta 443.
2. **Escalabilidade sob Carga de IA:** A execução de embeddings em CPU via Sentence-Transformers e busca vetorial no ChromaDB apresentou aumento de latência P95 (7,74s) sob concorrência 5 no endpoint RAG nos testes locais de contêineres, recomendando-se cache de embeddings ou aceleração dedicada para alta demanda concorrente em produção.
3. **Armazenamento de Backups no Disco da VM:** Recomenda-se replicação externa dos arquivos `.tar.gz` para Azure Blob Storage em produção.

---

## 8. Referências Técnicas no Pacote
- **Relatórios Técnicos e Matriz:**
  - `06_Relatorios/MATRIZ_CONFORMIDADE_FINAL_FECAP.md` (Matriz atualizada com 15 requisitos comprovados)
  - `06_Relatorios/RELATORIO_VALIDACAO_LOGS_HTTP_JSON.md` (Validação empírica de logs HTTP estruturados)
  - `06_Relatorios/PLANO_IMPLANTACAO_HTTPS_AZURE.md` (Plano técnico completo de HTTPS/TLS com Let's Encrypt)
  - `06_Relatorios/RELATORIO_CORRECOES_FINAIS_FECAP.md` (Sumário executivo de resolução das pendências)
  - `06_Relatorios/RELATORIO_LOGS_ESTRUTURADOS.md` (Auditoria de observabilidade RAG)
  - `06_Relatorios/RELATORIO_SEGURANCA_CONTROLE_ACESSO.md` (Auditoria de segurança, RBAC e segredos)
  - `06_Relatorios/RELATORIO_OTIMIZACOES_DESEMPENHO.md` (Auditoria de desempenho e otimizações)
- **Evidências:** `03_Evidencias/Ubuntu_evidencias(1).docx`, `03_Evidencias/load_test_results.json`, `03_Evidencias/backup_restore_evidence.json`
- **Configurações e Scripts:** `05_Configuracoes/docker-compose.yml`, `05_Configuracoes/docker-compose.azure.yml`, `05_Configuracoes/nginx.azure.conf`, `05_Configuracoes/nginx.conf`, `05_Configuracoes/Dockerfile.backend`, `05_Configuracoes/Dockerfile.frontend`, `05_Configuracoes/backup.sh`, `05_Configuracoes/restore.sh`
