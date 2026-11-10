#!/usr/bin/env bash
# ==============================================================================
# SecretarIA / FECAP Guia — Script de Preparação e Validação em Ubuntu 24.04 Azure
# Máquina Virtual Alvo: vm-fecap-secretaria
# ==============================================================================
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${PROJECT_DIR}"

echo "=================================================================="
echo " 1. Preparando diretórios persistentes e permissões"
echo "=================================================================="
mkdir -p ./backend/chroma_db ./backups ./deploy/certs ./deploy/certbot-www
touch ./backend/fecap_guia.db

if [ ! -f ./.env.azure ]; then
  echo "[INFO] Criando .env.azure a partir do template e gerando SECRET_KEY segura..."
  cp ./.env.azure.example ./.env.azure
  GENERATED_KEY="$(openssl rand -hex 32)"
  sed -i "s|SUBSTITUIR_COM_OPENSSL_RAND_HEX_32_NA_VM_AZURE|${GENERATED_KEY}|g" ./.env.azure
  chmod 600 ./.env.azure
  echo "[AVISO] Revise o arquivo .env.azure para ajustar BACKEND_CORS_ORIGINS com o IP/domínio público da VM."
else
  chmod 600 ./.env.azure
  echo "[OK] Arquivo .env.azure já existente (permissão 600 aplicada)."
fi

echo "=================================================================="
echo " 2. Configurando Firewall UFW (Exposição Mínima: 22, 80, 443)"
echo "=================================================================="
if command -v ufw >/dev/null 2>&1; then
  sudo ufw allow OpenSSH
  sudo ufw allow 80/tcp
  sudo ufw allow 443/tcp
  sudo ufw deny 8000/tcp
  sudo ufw deny 5173/tcp
  echo "[INFO] Regras UFW preparadas (80/443 abertas; 8000/5173 bloqueadas externamente)."
fi

echo "=================================================================="
echo " 3. Build e Inicialização via Docker Compose Azure"
echo "=================================================================="
docker compose -f docker-compose.azure.yml --env-file .env.azure up -d --build

echo "=================================================================="
echo " 4. Verificando Healthchecks e Comunicação pelo Proxy Reverso (:80)"
echo "=================================================================="
sleep 5
docker compose -f docker-compose.azure.yml ps
curl -fsS http://127.0.0.1/health && echo -e "\n[OK] Proxy reverso /health respondeu com sucesso!"
