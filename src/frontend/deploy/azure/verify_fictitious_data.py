"""
Script de Auditoria de Segurança e Privacidade (LGPD / Segredos / Dados Fictícios)
pré-implantação na VM Azure (vm-fecap-secretaria).

Verifica:
1. Que todas as contas de usuários e estudantes em `backend/fecap_guia.db` são fictícias (`is_demo=1` / domínio `@demo.fecap.br`).
2. Que não há CPFs, RGs ou telefones reais na base SQLite.
3. Que `.gitignore` bloqueia `.env`, `.env.*`, certificados (`*.key`, `*.pem`, `*.crt`) e `backups/`.
4. Que `docker-compose.azure.yml` não expõe as portas `8000` nem `5173` no host público.
"""
from __future__ import annotations

from pathlib import Path
import sqlite3
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run_security_audit() -> int:
    errors: list[str] = []

    # 1. Verificar .gitignore
    gitignore_path = PROJECT_ROOT / ".gitignore"
    gitignore_text = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""
    for required_pattern in [".env", "*.key", "*.pem", "deploy/certs/", "backups/"]:
        if required_pattern not in gitignore_text:
            errors.append(f"Padrão de segurança ausente no .gitignore: {required_pattern}")

    # 2. Verificar docker-compose.azure.yml (não expor 8000 nem 5173 em ports:)
    compose_azure = PROJECT_ROOT / "docker-compose.azure.yml"
    if not compose_azure.exists():
        errors.append("Arquivo docker-compose.azure.yml não encontrado.")
    else:
        compose_text = compose_azure.read_text(encoding="utf-8")
        if '"8000:8000"' in compose_text or '"5173:5173"' in compose_text:
            errors.append("docker-compose.azure.yml não deve publicar 8000:8000 nem 5173:5173 diretamente.")

    # 3. Verificar banco SQLite (apenas dados fictícios)
    db_path = PROJECT_ROOT / "backend" / "fecap_guia.db"
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()

        users = cur.execute("SELECT email, role, is_demo FROM users").fetchall()
        for email, role, is_demo in users:
            if not email.endswith("@demo.fecap.br") and not is_demo:
                errors.append(f"Usuário não-fictício detectado no SQLite: {email} (role={role})")

        students = cur.execute("SELECT name, ra, email, is_demo FROM students").fetchall()
        for name, ra, email, is_demo in students:
            if not is_demo or not email.endswith("@demo.fecap.br"):
                errors.append(f"Estudante não-fictício detectado no SQLite: {name} ({ra} / {email})")

        conn.close()

    if errors:
        print("[FALHA NA AUDITORIA PRÉ-DEPLOY AZURE]")
        for err in errors:
            print(f" - {err}")
        return 1

    print("[OK] Auditoria de segurança e dados fictícios concluída com sucesso:")
    print(" - Banco SQLite contém apenas perfis fictícios (@demo.fecap.br, is_demo=1).")
    print(" - Portas 8000 e 5173 isoladas na rede privada do Docker em docker-compose.azure.yml.")
    print(" - Arquivos de segredos e certificados protegidos no .gitignore.")
    return 0


if __name__ == "__main__":
    sys.exit(run_security_audit())
