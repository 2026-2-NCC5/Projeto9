"""
Seed do banco de dados — dados de DEMONSTRACAO.

AVISO: TODOS os dados abaixo sao FICTICIOS.
Nao representam estudantes, funcionarios ou documentos reais.
"""
import asyncio
from app.core.database import AsyncSessionLocal, create_tables
from app.core.security import hash_password
from app.core.config import settings


DEMO_USERS = [
    {
        "email": "estudante@demo.fecap.br",
        "password": "demo1234",
        "role": "student",
        "is_demo": True,
    },
    {
        "email": "estudante2@demo.fecap.br",
        "password": "demo1234",
        "role": "student",
        "is_demo": True,
    },
    {
        "email": settings.admin_default_email if hasattr(settings, "admin_default_email")
                 else "admin@demo.fecap.br",
        "password": "admin1234",
        "role": "admin",
        "is_demo": True,
    },
]

DEMO_STUDENTS = [
    {
        "email": "estudante@demo.fecap.br",
        "name": "Ana Demonstracao Silva",
        "ra": "DEMO001",
        "course": "Administracao",
        "period": "3o Semestre",
        "is_demo": True,
    },
    {
        "email": "estudante2@demo.fecap.br",
        "name": "Carlos Demonstracao Santos",
        "ra": "DEMO002",
        "course": "Ciencias Contabeis",
        "period": "1o Semestre",
        "is_demo": True,
    },
]

DEMO_DOCUMENTS = [
    {
        "title": "Como Acessar o Portal do Aluno",
        "category": "portal_sistemas",
        "origin": "Base de Demonstracao Academica",
        "version": "1.0-DEMO",
        "status": "active",
        "is_demo": True,
        "file_path": "knowledge_base/demo/portal_do_aluno.txt",
    },
    {
        "title": "Solicitacao de Documentos Academicos",
        "category": "documentos_certidoes",
        "origin": "Base de Demonstracao Academica",
        "version": "1.0-DEMO",
        "status": "active",
        "is_demo": True,
        "file_path": "knowledge_base/demo/solicitacao_documentos.txt",
    },
    {
        "title": "Declaracao de Matricula — Procedimento",
        "category": "documentos_certidoes",
        "origin": "Base de Demonstracao Academica",
        "version": "1.0-DEMO",
        "status": "active",
        "is_demo": True,
        "file_path": "knowledge_base/demo/declaracao_matricula.txt",
    },
    {
        "title": "Segunda Via de Documentos",
        "category": "documentos_certidoes",
        "origin": "Base de Demonstracao Academica",
        "version": "1.0-DEMO",
        "status": "active",
        "is_demo": True,
        "file_path": "knowledge_base/demo/segunda_via.txt",
    },
    {
        "title": "Atendimento Academico — Guia Completo",
        "category": "atendimento_suporte",
        "origin": "Base de Demonstracao Academica",
        "version": "1.0-DEMO",
        "status": "active",
        "is_demo": True,
        "file_path": "knowledge_base/demo/atendimento_academico.txt",
    },
    {
        "title": "Canais de Atendimento",
        "category": "atendimento_suporte",
        "origin": "Base de Demonstracao Academica",
        "version": "1.0-DEMO",
        "status": "active",
        "is_demo": True,
        "file_path": "knowledge_base/demo/canais_atendimento.txt",
    },
    {
        "title": "Procedimentos Administrativos — Guia do Estudante",
        "category": "procedimentos",
        "origin": "Base de Demonstracao Academica",
        "version": "1.0-DEMO",
        "status": "active",
        "is_demo": True,
        "file_path": "knowledge_base/demo/procedimentos_administrativos.txt",
    },
    {
        "title": "Perguntas Frequentes — FAQ do Estudante",
        "category": "faq",
        "origin": "Base de Demonstracao Academica",
        "version": "1.0-DEMO",
        "status": "active",
        "is_demo": True,
        "file_path": "knowledge_base/demo/faq.txt",
    },
]


async def seed():
    """Popula o banco com dados de demonstracao."""
    print("=" * 60)
    print("FECAP Guia — Seed de DEMONSTRACAO")
    print("ATENCAO: Todos os dados sao FICTICIOS")
    print("=" * 60)

    await create_tables()
    print("[OK] Tabelas criadas/verificadas")

    # Modelos serao importados nas proximas fases
    # Por enquanto apenas confirma que a estrutura existe
    print("[OK] Seed estrutura criada (modelos implementados na Fase 3)")
    print("")
    print("Dados de demonstracao que serao criados na Fase 3:")
    for u in DEMO_USERS:
        print(f"  - Usuario: {u['email']} ({u['role']})")
    for s in DEMO_STUDENTS:
        print(f"  - Estudante: {s['name']} | RA: {s['ra']}")
    for d in DEMO_DOCUMENTS:
        print(f"  - Documento: {d['title']}")
    print("")
    print("[OK] Seed concluido!")


if __name__ == "__main__":
    asyncio.run(seed())
