# Relatório Técnico — Fase 8: Conteinerização e Execução Local com Docker Compose (FECAP Guia / SecretarIA)

**Data da Execução:** 01/11/2026  
**Projeto:** `C:\SecretaRIA\fecap-guia`  
**Ambiente Host:** Windows + WSL 2 + Ubuntu + Docker Desktop (`Docker 29.9.2`, `Docker Compose v5.6.1`)  
**Status Geral da Fase 8:** ✅ **CONCLUÍDA E VALIDADA COM SUCESSO (100% dos testes aprovados)**

---

## 1. Inspeção Inicial dos Arquivos Docker e Infraestrutura

Foram inspecionados os arquivos de orquestração e empacotamento existentes no projeto:
- [docker-compose.yml](file:///C:/SecretaRIA/fecap-guia/docker-compose.yml)
- [backend/Dockerfile](file:///C:/SecretaRIA/fecap-guia/backend/Dockerfile)
- [frontend/Dockerfile](file:///C:/SecretaRIA/fecap-guia/frontend/Dockerfile)
- [frontend/nginx.conf](file:///C:/SecretaRIA/fecap-guia/frontend/nginx.conf)

### Achados Técnicos e Correções Realizadas (Sem Recriar ou Alterar Funcionalidades)
1. **Persistência de Dados Existentes (SQLite + ChromaDB):**
   - O `docker-compose.yml` original forçava `DATABASE_URL: postgresql://...` e montava um volume nomeado vazio `chroma_data:/app/chroma_db`, o que ocultaria os dados já existentes no host (`backend/fecap_guia.db` com 413 KB e `backend/chroma_db` com 55 chunks indexados na coleção `fecap_knowledge`).
   - **Solução aplicada:** Configurado `DATABASE_URL: sqlite:///./fecap_guia.db` e `CHROMA_PERSIST_DIRECTORY: ./chroma_db`, mantendo o bind mount `./backend:/app` e `./knowledge_base:/app/knowledge_base`. O serviço PostgreSQL (`db`) foi preservado integralmente no `docker-compose.yml` sob o profile `prod` (`--profile prod`) para futura migração em nuvem.
2. **Alinhamento de Dependências do Backend ([backend/requirements.txt](file:///C:/SecretaRIA/fecap-guia/backend/requirements.txt)):**
   - O banco `backend/chroma_db/chroma.sqlite3` existente foi criado com schema do **ChromaDB 1.5.9** (Rust bindings), enquanto o `requirements.txt` antigo listava `chromadb==0.5.0` e omitia `email-validator` (exigido pelo `EmailStr` do Pydantic) e `greenlet` (exigido pelo `sqlalchemy.ext.asyncio` em Linux). Além disso, listava `torch` sem índice CPU, o que baixaria ~2.5 GB de binários CUDA desnecessários.
   - **Solução aplicada:** Atualizado `backend/requirements.txt` com `--extra-index-url https://download.pytorch.org/whl/cpu`, `chromadb==1.5.9`, `sentence-transformers==6.2.0`, `fastapi==0.141.1`, `sqlalchemy==2.1.6`, `greenlet==3.5.6`, `email-validator>=2.0.0` e `google-genai==2.25.0`.
3. **Pré-carregamento do Modelo `all-MiniLM-L6-v2` ([backend/Dockerfile](file:///C:/SecretaRIA/fecap-guia/backend/Dockerfile)):**
   - Adicionada etapa de build `RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"` para embutir o modelo de embeddings diretamente na imagem Docker, evitando lentidão ou falha de rede na primeira requisição RAG.
4. **Correção de BOM UTF-8 no Nginx ([frontend/nginx.conf](file:///C:/SecretaRIA/fecap-guia/frontend/nginx.conf)):**
   - O arquivo `frontend/nginx.conf` possuía bytes UTF-8 BOM (`EF BB BF`) no início da linha 1, causando erro no Nginx Alpine (`unknown directive "server" in /etc/nginx/conf.d/default.conf:1`). O arquivo foi salvo em UTF-8 puro (sem BOM) e adicionado `HEALTHCHECK` ao [frontend/Dockerfile](file:///C:/SecretaRIA/fecap-guia/frontend/Dockerfile).
5. **Isolamento de Diretórios de Contexto (`.dockerignore`):**
   - Criados [backend/.dockerignore](file:///C:/SecretaRIA/fecap-guia/backend/.dockerignore) e [frontend/.dockerignore](file:///C:/SecretaRIA/fecap-guia/frontend/.dockerignore) para impedir o envio de `node_modules`, `.env`, caches e bancos locais para a camada estática da imagem durante o build.

---

## 2. Verificação de Dependências da Stack

| Componente | Versão / Configuração Verificada | Status |
| :--- | :--- | :--- |
| **Backend (FastAPI + Uvicorn)** | Python `3.11.18-slim` + `fastapi==0.141.1` + `uvicorn==0.54.0` | ✅ Operacional |
| **Frontend (React + Vite + Nginx)** | Build Node `20-alpine` (`tsc && vite build`) + runtime `nginx:alpine` (porta `5173`) | ✅ Operacional |
| **Banco Relacional (SQLite)** | `sqlalchemy==2.1.6` + `aiosqlite==0.22.1` + `greenlet==3.5.6` (`fecap_guia.db`) | ✅ Persistente |
| **Banco Vetorial (ChromaDB)** | `chromadb==1.5.9` (`PersistentClient` em `/app/chroma_db`, coleção `fecap_knowledge`) | ✅ Persistente |
| **Modelo de Embeddings (MiniLM)** | `sentence-transformers==6.2.0` (`all-MiniLM-L6-v2`, `device=cpu`, pré-cacheado na imagem) | ✅ Operacional |

---

## 3. Configuração de Variáveis de Ambiente, Rede e Healthchecks

### Variáveis de Ambiente (Sem Exposição de Segredos)
As variáveis sensíveis (`SECRET_KEY`, `GOOGLE_API_KEY`, `ADMIN_DEFAULT_PASSWORD`) permanecem exclusivamente em `backend/.env` (ignorado pelo Git e pelo `.dockerignore`) e são injetadas em runtime via `env_file`. No `docker-compose.yml`, foram declaradas apenas variáveis estruturais não-sensíveis:
- `DATABASE_URL: sqlite:///./fecap_guia.db`
- `CHROMA_PERSIST_DIRECTORY: ./chroma_db`
- `CHROMA_COLLECTION_NAME: fecap_knowledge`
- `EMBEDDING_MODEL: all-MiniLM-L6-v2`
- `EMBEDDING_DEVICE: cpu`
- `BACKEND_CORS_ORIGINS: http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000`
- `VITE_API_URL: http://localhost:8000`

### Rede e Healthchecks
- **Rede dedicada:** `fecap_net` (`fecap_guia_network`, driver `bridge`), conectando `fecap_guia_frontend` e `fecap_guia_backend` com resolução DNS interna (permitindo `proxy_pass http://backend:8000;` no Nginx).
- **Healthcheck Backend:** `curl -f http://localhost:8000/health` (intervalo 15s, timeout 10s, 5 tentativas, start_period 30s).
- **Healthcheck Frontend:** `wget -q -O /dev/null http://127.0.0.1:5173/ || exit 1` (intervalo 15s, timeout 10s, 3 tentativas, start_period 10s).
- **Ordem de inicialização:** `frontend` aguarda `backend` atingir `condition: service_healthy`.

---

## 4. Persistência de Dados Verificada (Antes x Depois)

Nenhum dado existente foi apagado. A leitura direta dos bancos antes e após a subida dos contêineres e execução dos testes comprova a persistência integral via bind mount:

| Estrutura / Tabela | Registros Antes do Docker | Registros Após Testes e Validações | Status |
| :--- | :---: | :---: | :--- |
| SQLite: `users` | 3 | 3 | ✅ Preservado |
| SQLite: `students` | 2 | 2 | ✅ Preservado |
| SQLite: `knowledge_documents` | 14 | 18 | ✅ Preservado + Novos testes |
| SQLite: `conversations` | 26 | 34 | ✅ Preservado + Novos testes |
| SQLite: `messages` | 50 | 64 | ✅ Preservado + Novos testes |
| SQLite: `handoff_tickets` | 11 | 15 | ✅ Preservado + Novos testes |
| SQLite: `feedbacks` | 8 | 10 | ✅ Preservado + Novos testes |
| SQLite: `human_validations` | 4 | 6 | ✅ Preservado + Novos testes |
| SQLite: `audit_logs` | 218 | 291 | ✅ Preservado + Novos testes |
| ChromaDB: `fecap_knowledge` | 55 chunks | 55 chunks ativos | ✅ Preservado |

---

## 5. Validação da Comunicação entre Serviços (Frontend ↔ API ↔ Banco ↔ RAG)

Foram executadas chamadas reais aos contêineres em execução:

1. **Healthcheck da API (`GET http://localhost:8000/health`):**
   - Retorno: `200 OK` -> `{"status":"ok","version":"1.0.0","env":"development","llm_mode":"demo","demo_mode":true}`
2. **Servidor Frontend (`GET http://localhost:5173/`):**
   - Retorno: `200 OK` (HTML da SPA React entregue pelo Nginx).
3. **Autenticação JWT + SQLite (`POST http://localhost:8000/api/v1/auth/login`):**
   - Login com `estudante@demo.fecap.br` retornou `200 OK` com `access_token` e `refresh_token`.
4. **Proxy Reverso Nginx Frontend → Backend (`GET http://localhost:5173/api/v1/student/profile`):**
   - Retorno: `200 OK` -> `{"name":"Ana Demonstracao Silva","ra":"DEMO001","course":"Administracao","period":"3o Semestre","email":"estudante@demo.fecap.br",...}`
5. **Agente RAG + ChromaDB + MiniLM (`POST http://localhost:8000/api/v1/agent/query`):**
   - Pergunta: *"Como emitir declaracao de matricula no Portal do Aluno?"*
   - Retorno: `200 OK` | `confidence: 0.6809` | `requires_human: false` | `evidence: 5 chunks recuperados` | `source: "rag_pipeline"`.

---

## 6. Logs, Consumo de CPU e Memória (`docker stats`)

### Status dos Contêineres (`docker compose ps`)
```text
NAME                  IMAGE                 COMMAND                  SERVICE    STATUS                        PORTS
fecap_guia_backend    fecap-guia-backend    "uvicorn app.main:ap…"   backend    Up (healthy)                  0.0.0.0:8000->8000/tcp
fecap_guia_frontend   fecap-guia-frontend   "/docker-entrypoint.…"   frontend   Up (healthy)                  0.0.0.0:5173->5173/tcp
```

### Consumo de Recursos (`docker stats --no-stream`)
| Contêiner | CPU % | Uso de Memória / Limite | MEM % | NET I/O | Processos (PIDs) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `fecap_guia_frontend` (Nginx Alpine) | `0.00%` | `8.67 MiB / 7.69 GiB` | `0.11%` | `3.22 kB / 3.59 kB` | `5` |
| `fecap_guia_backend` (FastAPI + MiniLM + ChromaDB) | `0.25%` | `436.60 MiB / 7.69 GiB` | `5.54%` | `71.8 kB / 31.5 kB` | `31` |

---

## 7. Execução dos Testes Automatizados (Regressão Zero)

### Testes do Backend (Executados dentro do contêiner `fecap_guia_backend`)
- **Comando:** `docker exec -e PYTHONPATH=/app fecap_guia_backend pytest /tests/backend -v`
- **Resultado:** **`36 passed in 115.35s`** (0 falhas, 0 erros)
  - `test_admin_phase6.py`: 6/6 aprovados (Dashboard RBAC, CRUD Base de Conhecimento, Upload TXT, RF-08 Validação Humana, Handoff Admin, Sanitização de Auditoria).
  - `test_auth_and_api.py`: 11/11 aprovados (Login, Refresh, Expiração, Perfil, Isolamento de Histórico, Feedbacks RBAC, Handoff Protocolo, Auditoria RBAC, Persistência de Conversa RAG).
  - `test_models_and_database.py`: 4/4 aprovados (Modelos SQLAlchemy e relacionamentos).
  - `test_rag_pipeline.py`: 10/10 aprovados (Validação de pergunta vazia, Mediana de Confiança, Filtro de Evidência, Modo Demo, Abstenção Responsável, Modo Gemini Mock, Fallback de Erro, Endpoint `/api/v1/agent/query`, Status e Compatibilidade de Schema).
  - `test_vector_store.py`: 5/5 aprovados (Chunker com overlap, Persistência e Idempotência no ChromaDB, Precisão da Busca Semântica com `all-MiniLM-L6-v2`, Desindexação ao inativar documento, Query vazia).
  - *Nota técnica:* A fixture `vector_test_env` em [tests/backend/test_vector_store.py](file:///C:/SecretaRIA/fecap-guia/tests/backend/test_vector_store.py) foi aprimorada para utilizar `tmp_path` nativo do Pytest em vez de diretório fixo em bind mount, evitando bloqueio de descritor SQLite no kernel Linux durante o teardown entre testes.

### Testes do Frontend
- **Comando:** `npm test -- --run` (em `C:\SecretaRIA\fecap-guia\frontend`)
- **Resultado:** **`4 passed (1 test file)`** (`src/store/stores.test.ts` — `authStore` login/logout/RBAC e `chatStore` RAG).

---

## 8. Comandos Executados (Documentação para Reprodução)

```powershell
# 1. Verificar instalação do Docker e Docker Compose
docker --version
docker compose version

# 2. Construir imagens e iniciar contêineres em background
cd C:\SecretaRIA\fecap-guia
docker compose up -d --build

# 3. Verificar status e healthchecks dos contêineres
docker compose ps
docker ps

# 4. Inspecionar consumo de CPU e Memória em tempo real
docker stats --no-stream

# 5. Inspecionar logs dos serviços
docker compose logs --tail 50

# 6. Testar endpoints de saúde e comunicação
curl http://localhost:8000/health
curl -I http://localhost:5173

# 7. Executar a suíte completa de testes do Backend dentro do contêiner Docker
docker exec -e PYTHONPATH=/app fecap_guia_backend pytest /tests/backend -v

# 8. Executar a suíte de testes do Frontend
cd C:\SecretaRIA\fecap-guia\frontend
npx vitest run
```

---

## 9. Roteiro de Capturas de Tela (Prints) para a Entrega da FECAP

Para compor a documentação de entrega acadêmica da Fase 8, capture as seguintes **8 telas**:

1. **Print 1 — Terminal com `docker compose ps` e `docker stats --no-stream`:**
   - Execute no PowerShell dentro de `C:\SecretaRIA\fecap-guia`:
     ```powershell
     docker compose ps; docker stats --no-stream
     ```
   - **O que comprova:** Ambos os contêineres (`fecap_guia_backend` e `fecap_guia_frontend`) ativos, com status `(healthy)`, portas `8000` e `5173` mapeadas e baixo consumo de CPU/RAM (~436 MiB no backend e ~8.6 MiB no frontend).

2. **Print 2 — Interface do Docker Desktop (Aba *Containers*):**
   - Abra o aplicativo **Docker Desktop** no Windows e clique em **Containers**.
   - Expanda o grupo `fecap-guia` mostrando `fecap_guia_backend` e `fecap_guia_frontend` em verde (*Running*).
   - **O que comprova:** Orquestração local via Docker Desktop + WSL 2 em funcionamento.

3. **Print 3 — Navegador no Endpoint `/health` e Swagger UI (`/docs`):**
   - Acesse `http://localhost:8000/health` e `http://localhost:8000/docs` no navegador.
   - **O que comprova:** API FastAPI respondendo do contêiner com todos os endpoints documentados no OpenAPI/Swagger.

4. **Print 4 — Navegador no Frontend Containerizado (Login e Chat RAG do Estudante):**
   - Acesse `http://localhost:5173/login`, entre com `estudante@demo.fecap.br` / `demo1234`, envie a pergunta *"Como solicitar declaração de matrícula?"* no chat e expanda os cards de **Evidências** e **Passos**.
   - **O que comprova:** Comunicação completa Frontend (Nginx `5173`) → API (`8000`) → ChromaDB + MiniLM → Resposta com evidências e score de confiança.

5. **Print 5 — Navegador no Painel Administrativo Containerizado (`/admin/dashboard` e `/admin/knowledge`):**
   - Acesse `http://localhost:5173/admin/login`, entre com `admin@demo.fecap.br` / `admin1234` e capture o **Dashboard Operacional** e a **Base de Conhecimento** mostrando os documentos e contagens preservados do banco SQLite/ChromaDB.
   - **O que comprova:** Persistência dos dados históricos no SQLite e ChromaDB sem perda de registros.

6. **Print 6 — Terminal com Execução dos 36 Testes Automatizados no Contêiner:**
   - Execute no PowerShell:
     ```powershell
     docker exec -e PYTHONPATH=/app fecap_guia_backend pytest /tests/backend -v
     ```
   - Capture a tela final mostrando `36 passed`.
   - **O que comprova:** Ausência de regressões nas Fases 1 a 8 dentro do ambiente Linux containerizado.

---

## 10. Pendências e Recomendações para Publicação em Nuvem (Próxima Fase)

> ⚠️ **Nota de Conformidade:** Conforme suas regras, **nenhuma publicação em nuvem foi realizada**. Abaixo estão os pontos mapeados para quando você autorizar a etapa de deploy em nuvem:

1. **Banco de Dados em Produção (PostgreSQL Gerenciado):**
   - Em nuvem (Render, Railway, Fly.io, Cloud Run ou Azure App Service), substituir o SQLite local ativando o perfil `prod` (`DATABASE_URL=postgresql://...`) ou conectando a um PostgreSQL gerenciado (Neon, Supabase ou Cloud SQL) e executar as migrações com Alembic.
2. **Persistência do Volume Vetorial (`chroma_db`) em Nuvem:**
   - Serviços serverless efêmeros apagam o disco local a cada deploy. Para manter o ChromaDB persistente em nuvem, deve-se anexar um **Persistent Volume / Disk** montado em `/app/chroma_db` ou executar o job de indexação (`index_all_active_documents`) no evento de startup caso a coleção esteja vazia.
3. **Variáveis de Ambiente e Segredos no Provedor Cloud:**
   - Configurar `SECRET_KEY` (gerada com 64 caracteres hexadecimais), `ADMIN_DEFAULT_PASSWORD` forte, `APP_ENV=production`, `DEBUG=false` e `BACKEND_CORS_ORIGINS` apontando para o domínio HTTPS oficial do frontend.
   - Se desejar ativar geração via LLM em nuvem (`LLM_MODE=gemini`), configurar `GOOGLE_API_KEY` no cofre de segredos do provedor e atualizar `GEMINI_MODEL=gemini-2.5-flash`.
4. **Remoção do Bind Mount de Código em Produção:**
   - No `docker-compose.yml` de produção, remover os bind mounts de desenvolvimento (`./backend:/app` e `./tests:/tests`), mantendo apenas os volumes persistentes de dados, pois o código já está copiado dentro da imagem Docker.
