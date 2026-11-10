#!/usr/bin/env bash
# ==============================================================================
# SecretarIA / FECAP Guia — Script de Backup Consistente (SQLite + ChromaDB)
# Ambiente alvo: Ubuntu 24.04 LTS (vm-fecap-secretaria)
# ==============================================================================
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKUP_ROOT="${PROJECT_DIR}/backups"
TIMESTAMP="$(date -u +"%Y%m%dT%H%M%SZ")"
DEST_DIR="${BACKUP_ROOT}/backup_${TIMESTAMP}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

mkdir -p "${DEST_DIR}"

echo "[INFO] Iniciando backup em ${DEST_DIR}..."

# 1. Backup consistente do SQLite usando a API online de backup do Python sqlite3
if docker ps --format '{{.Names}}' | grep -q '^fecap_guia_backend$'; then
  echo "[INFO] Executando backup online consistente do SQLite via contêiner fecap_guia_backend..."
  docker exec fecap_guia_backend python -c "
import sqlite3
src = sqlite3.connect('/app/fecap_guia.db')
dst = sqlite3.connect('/backups/fecap_guia_snapshot_${TIMESTAMP}.db')
with dst:
    src.backup(dst)
dst.close()
src.close()
"
  mv "${BACKUP_ROOT}/fecap_guia_snapshot_${TIMESTAMP}.db" "${DEST_DIR}/fecap_guia.db"
elif [ -f "${PROJECT_DIR}/backend/fecap_guia.db" ]; then
  echo "[INFO] Contêiner parado. Copiando backend/fecap_guia.db diretamente..."
  cp -a "${PROJECT_DIR}/backend/fecap_guia.db" "${DEST_DIR}/fecap_guia.db"
else
  echo "[WARN] Arquivo backend/fecap_guia.db não encontrado."
fi

# 2. Backup do diretório persistente do ChromaDB
if [ -d "${PROJECT_DIR}/backend/chroma_db" ]; then
  echo "[INFO] Compactando diretório persistente backend/chroma_db..."
  tar -czf "${DEST_DIR}/chroma_db.tar.gz" -C "${PROJECT_DIR}/backend" chroma_db
fi

# 3. Backup da base textual knowledge_base
if [ -d "${PROJECT_DIR}/knowledge_base" ]; then
  tar -czf "${DEST_DIR}/knowledge_base.tar.gz" -C "${PROJECT_DIR}" knowledge_base
fi

# 4. Gerar manifesto SHA-256
(
  cd "${DEST_DIR}"
  sha256sum * > sha256sums.txt
)

# 5. Empacotar arquivo final .tar.gz
ARCHIVE_FILE="${BACKUP_ROOT}/fecap_guia_backup_${TIMESTAMP}.tar.gz"
tar -czf "${ARCHIVE_FILE}" -C "${BACKUP_ROOT}" "backup_${TIMESTAMP}"
rm -rf "${DEST_DIR}"

# 6. Limpeza de backups antigos
find "${BACKUP_ROOT}" -maxdepth 1 -name "fecap_guia_backup_*.tar.gz" -mtime +"${RETENTION_DAYS}" -delete || true

echo "[OK] Backup concluído com sucesso: ${ARCHIVE_FILE}"
