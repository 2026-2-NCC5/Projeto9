# SecretarIA - Secretaria Acadêmica Inteligente

> **Projeto Interdisciplinar de Inteligência Artificial — ASA/FECAP**

> ⚠️ **AVISO — PROJETO ACADÊMICO**: Este projeto utiliza **dados fictícios de demonstração**.
> Nenhuma informação é oficial. Todos os dados de estudantes e documentos são **DEMONSTRAÇÃO**.

---

## Sobre o Projeto

A **SecretarIA** (Secretaria Acadêmica Inteligente ASA/FECAP) é um agente de atendimento e orientação baseado em **RAG (Retrieval-Augmented Generation)** com suporte ao modelo **Gemini 2.5 Flash**.
Responde a dúvidas sobre serviços acadêmicos e procedimentos operacionais usando exclusivamente a base do Regimento Geral Oficial da FECAP.

### Diferenciais
- 🔍 **Orientação com evidências** — toda resposta apresenta documento fonte, versão e data
- 📋 **Passo a passo estruturado** — resposta + etapas + próxima ação
- 🛑 **Abstinência responsável** — sem evidência suficiente, o sistema NÃO inventa
- 🤝 **Encaminhamento humano** — fluxo de handoff integrado
- 🔒 **Privacidade por design** — minimização de dados, logs de auditoria

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| Backend | Python 3.11 + FastAPI |
| Banco (dev) | SQLite |
| Banco (prod) | PostgreSQL |
| Auth | JWT + bcrypt |
| RAG Embeddings | sentence-transformers (MiniLM) |
| Vector Store | ChromaDB |
| LLM | Google Gemini / Modo DEMO local |
| Containers | Docker + Docker Compose |

---

## Início Rápido

### Docker (recomendado)

```bash
git clone <url>
cd fecap-guia
cp backend/.env.example backend/.env
docker compose up --build
```

- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs
- Health:   http://localhost:8000/health

### Desenvolvimento local

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env           # edite conforme necessário
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --port 8000

# Frontend (outro terminal)
cd frontend
npm install
npm run dev
```

---

## Credenciais Demo (FICTÍCIAS)

| Tipo | E-mail | Senha |
|------|--------|-------|
| Estudante | `estudante@demo.fecap.br` | `demo1234` |
| Admin | `admin@demo.fecap.br` | `admin1234` |

---

## Modo do Agente

```env
LLM_MODE=demo    # Padrão: sem API key, 100% local
LLM_MODE=gemini  # Com GOOGLE_API_KEY configurada
```

---

## Documentação

| Documento | Descrição |
|-----------|-----------|
| [Arquitetura](docs/architecture.md) | Diagrama e decisões |
| [API](docs/api.md) | Referência da API |
| [Segurança](docs/security.md) | Controles de segurança |
| [Privacidade](docs/privacy.md) | Conformidade LGPD |
| [Agente](docs/agent.md) | Funcionamento RAG |
| [Base de Conhecimento](docs/knowledge-base.md) | Gestão de documentos |
| [Deploy](docs/deployment.md) | Instruções de implantação |
| [Testes](docs/testing.md) | Estratégia de testes |
| [Model Card](docs/MODEL_CARD.md) | Documentação do modelo |
| [Requisitos](docs/requirements-mapping.md) | RF/RNF → implementação |

---

## Testes

```bash
cd backend
pytest tests/ -v
pytest tests/ --cov=app --cov-report=html
```

---

## Fases de Desenvolvimento

| Fase | Status | Descrição |
|------|--------|-----------|
| 1 | ✅ | Arquitetura + Estrutura + Docs |
| 2 | 🔜 | Frontend + Telas |
| 3 | 🔜 | Backend + Banco + Auth |
| 4 | 🔜 | Base de Conhecimento |
| 5 | 🔜 | RAG + Agente |
| 6–14 | 🔜 | ... |

> ⚠️ Nunca commite `.env` com credenciais reais.
