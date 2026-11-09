#!/usr/bin/env bash
# ==============================================================================
# SecretarIA / FECAP Guia — Script de Restauração de Backup (SQLite + ChromaDB)
# Ambiente alvo: Ubuntu 24.04 LTS (vm-fecap-secretaria)
# Uso: ./deploy/azure/restore.sh ./backups/fecap_guia_backup_YYYYMMDDTHHMMSSZ.tar.gz
# Compatibilidade de caminhos:
# - Detecta automaticamente a raiz do projeto em `deploy/azure/restore.sh` (../..),
#   em subpastas de 1 nível (..) ou via variável de ambiente PROJECT_DIR.
# ==============================================================================
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Uso: $0 <caminho_do_arquivo_backup.tar.gz>"
  exit 1
fi

ARCHIVE_FILE="$1"
if [ ! -f "${ARCHIVE_FILE}" ]; then
  echo "[ERRO] Arquivo de backup não encontrado: ${ARCHIVE_FILE}"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -n "${PROJECT_DIR:-}" ]; then
  PROJECT_DIR="$(cd "${PROJECT_DIR}" && pwd)"
elif [ -d "${SCRIPT_DIR}/../../backend" ]; then
  PROJECT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
elif [ -d "${SCRIPT_DIR}/../backend" ]; then
  PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
else
  PROJECT_DIR="$(pwd)"
fi

TMP_RESTORE="$(mktemp -d)"
trap 'rm -rf "${TMP_RESTORE}"' EXIT

echo "[INFO] Diretório raiz do projeto resolvido para: ${PROJECT_DIR}"
echo "[INFO] Extraindo ${ARCHIVE_FILE}..."
tar -xzf "${ARCHIVE_FILE}" -C "${TMP_RESTORE}"
EXTRACTED_SUBDIR="$(find "${TMP_RESTORE}" -mindepth 1 -maxdepth 1 -type d | head -n 1)"

echo "[INFO] Verificando integridade SHA-256..."
(
  cd "${EXTRACTED_SUBDIR}"
  sha256sum -c sha256sums.txt
)

echo "[INFO] Parando contêineres antes de restaurar os bancos..."
docker compose -f "${PROJECT_DIR}/docker-compose.azure.yml" stop backend || true

# Salva cópia de segurança do estado anterior à restauração
PRE_RESTORE_TS="$(date -u +"%Y%m%dT%H%M%SZ")"
mkdir -p "${PROJECT_DIR}/backups/pre_restore_${PRE_RESTORE_TS}"
[ -f "${PROJECT_DIR}/backend/fecap_guia.db" ] && cp -a "${PROJECT_DIR}/backend/fecap_guia.db" "${PROJECT_DIR}/backups/pre_restore_${PRE_RESTORE_TS}/"
[ -d "${PROJECT_DIR}/backend/chroma_db" ] && cp -a "${PROJECT_DIR}/backend/chroma_db" "${PROJECT_DIR}/backups/pre_restore_${PRE_RESTORE_TS}/"

# Restaura SQLite
if [ -f "${EXTRACTED_SUBDIR}/fecap_guia.db" ]; then
  cp -a "${EXTRACTED_SUBDIR}/fecap_guia.db" "${PROJECT_DIR}/backend/fecap_guia.db"
  echo "[OK] Banco SQLite restaurado em backend/fecap_guia.db"
fi

# Restaura ChromaDB
if [ -f "${EXTRACTED_SUBDIR}/chroma_db.tar.gz" ]; then
  rm -rf "${PROJECT_DIR}/backend/chroma_db"
  tar -xzf "${EXTRACTED_SUBDIR}/chroma_db.tar.gz" -C "${PROJECT_DIR}/backend"
  echo "[OK] Diretório ChromaDB restaurado em backend/chroma_db"
fi

echo "[INFO] Reiniciando contêineres..."
docker compose -f "${PROJECT_DIR}/docker-compose.azure.yml" --env-file "${PROJECT_DIR}/.env.azure" up -d

echo "[OK] Restauração concluída com sucesso."
