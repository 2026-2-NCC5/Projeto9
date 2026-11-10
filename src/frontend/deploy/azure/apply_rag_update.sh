#!/usr/bin/env bash
# ==============================================================================
# SecretarIA / FECAP Guia — Script de Atualizacao Controlada do RAG Hibrido
# Maquina Virtual Alvo: vm-fecap-secretaria (Ubuntu 24.04 LTS)
# ==============================================================================
set -euo pipefail

PROJECT_DIR="/home/azureuser/fecap-guia-azure"
cd "${PROJECT_DIR}"

echo "=================================================================="
echo " 1. Verificacao Pre-Deploy de Integridade e Pre-requisitos"
echo "=================================================================="
if [ ! -f .env.azure ]; then
  echo "[ERRO CRITICO] Arquivo .env.azure nao encontrado em ${PROJECT_DIR}!"
  exit 1
fi

echo "[INFO] Testando resposta atual do conteiner antes do deploy..."
curl -fsS http://127.0.0.1/health || {
  echo "[ERRO] O sistema atual nao esta respondendo em /health!"
  exit 1
}

echo "=================================================================="
echo " 2. Executando Backup Preventivo Pre-Deploy (SQLite + Codigo)"
echo "=================================================================="
TIMESTAMP="$(date -u +"%Y%m%dT%H%M%SZ")"
BACKUP_DIR="${PROJECT_DIR}/backups/pre_rag_update_${TIMESTAMP}"
mkdir -p "${BACKUP_DIR}"

# 2.1 Backup consistente do SQLite online
docker exec fecap_guia_backend python -c "
import sqlite3
src = sqlite3.connect('/app/fecap_guia.db')
dst = sqlite3.connect('/backups/pre_rag_update_${TIMESTAMP}/fecap_guia.db')
with dst:
    src.backup(dst)
dst.close()
src.close()
"
echo "[OK] Backup consistente do SQLite salvo em ${BACKUP_DIR}/fecap_guia.db"

# 2.2 Backup dos arquivos de codigo que serao modificados
cp -a backend/app/agent/rag_pipeline.py "${BACKUP_DIR}/rag_pipeline.py.bak"
cp -a frontend/src/components/chat/StepsCard.tsx "${BACKUP_DIR}/StepsCard.tsx.bak"
echo "[OK] Backup do codigo anterior preservado em ${BACKUP_DIR}"

echo "=================================================================="
echo " 3. Aplicando Atualizacoes de Codigo (RAG Hibrido + StepsCard)"
echo "=================================================================="
# Copia os arquivos atualizados do pacote de staging para o projeto
# (Garante que .env.azure, deploy/certs, fecap_guia.db e chroma_db NUNCA sejam tocados)
if [ -d "${PROJECT_DIR}/update_pkg" ]; then
  cp -a "${PROJECT_DIR}/update_pkg/rag_pipeline.py" backend/app/agent/rag_pipeline.py
  cp -a "${PROJECT_DIR}/update_pkg/StepsCard.tsx" frontend/src/components/chat/StepsCard.tsx
fi

echo "=================================================================="
echo " 4. Reiniciando Backend e Recompilando Frontend (Docker Compose)"
echo "=================================================================="
# Reinicia o backend para carregar a nova logica do rag_pipeline.py
docker compose -f docker-compose.azure.yml --env-file .env.azure restart backend

# Recompila o frontend React com o novo StepsCard.tsx e atualiza o container sem mexer nos certificados
docker compose -f docker-compose.azure.yml --env-file .env.azure build frontend
docker compose -f docker-compose.azure.yml --env-file .env.azure up -d --no-deps frontend

echo "=================================================================="
echo " 5. Validacao Pos-Deploy e Healthchecks"
echo "=================================================================="
sleep 5
docker compose -f docker-compose.azure.yml ps

echo "[TESTE 1/3] Validando endpoint /health..."
curl -fsS http://127.0.0.1/health && echo -e "\n[OK] Healthcheck 200 OK!"

echo "[TESTE 2/3] Validando status do agente /api/v1/agent/..."
curl -fsS http://127.0.0.1/api/v1/agent/ && echo -e "\n[OK] Agente online!"

echo "[TESTE 3/3] Validando consulta RAG no proxy reverso..."
curl -fsS -X POST http://127.0.0.1/api/v1/agent/query \
  -H "Content-Type: application/json" \
  -d '{"question":"Como trancar materia?"}' | grep -q "Trancamento" && echo -e "[OK] RAG Hibrido respondendo estruturado!"

echo "=================================================================="
echo " ATUALIZACAO CONCLUIDA COM SUCESSO!"
echo "=================================================================="
