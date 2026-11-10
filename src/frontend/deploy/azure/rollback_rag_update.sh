#!/usr/bin/env bash
# ==============================================================================
# SecretarIA / FECAP Guia — Script de Rollback Imediato
# Maquina Virtual Alvo: vm-fecap-secretaria (Ubuntu 24.04 LTS)
# ==============================================================================
set -euo pipefail

PROJECT_DIR="/home/azureuser/fecap-guia-azure"
cd "${PROJECT_DIR}"

LATEST_PRE_UPDATE="$(ls -dt ${PROJECT_DIR}/backups/pre_rag_update_* 2>/dev/null | head -n 1)"

if [ -z "${LATEST_PRE_UPDATE}" ] || [ ! -d "${LATEST_PRE_UPDATE}" ]; then
  echo "[ERRO] Nenhum diretorio de backup pre-deploy encontrado em ${PROJECT_DIR}/backups!"
  exit 1
fi

echo "[INFO] Restaurando codigo do backup: ${LATEST_PRE_UPDATE}"
cp -a "${LATEST_PRE_UPDATE}/rag_pipeline.py.bak" backend/app/agent/rag_pipeline.py
cp -a "${LATEST_PRE_UPDATE}/StepsCard.tsx.bak" frontend/src/components/chat/StepsCard.tsx

echo "[INFO] Reiniciando backend..."
docker compose -f docker-compose.azure.yml --env-file .env.azure restart backend

echo "[INFO] Reconstruindo frontend..."
docker compose -f docker-compose.azure.yml --env-file .env.azure build frontend
docker compose -f docker-compose.azure.yml --env-file .env.azure up -d --no-deps frontend

echo "[INFO] Testando restabelecimento..."
sleep 5
curl -fsS http://127.0.0.1/health
echo -e "\n[OK] Rollback concluido e servicos restabelecidos!"
