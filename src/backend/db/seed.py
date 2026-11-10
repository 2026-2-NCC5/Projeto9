"""
Seed do banco de dados - dados de DEMONSTRACAO.

AVISO: TODOS os dados abaixo sao FICTICIOS.
Nao representam estudantes, funcionarios ou documentos reais.
"""
import os
import asyncio
from datetime import datetime, timezone
from sqlalchemy import select

from app.core.database import AsyncSessionLocal, create_tables
from app.core.security import hash_password
from app.core.config import settings
from app.models import User, Student, KnowledgeDocument


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
        "email": getattr(settings, "admin_default_email", "admin@demo.fecap.br"),
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
        "title": "Declaracao de Matricula - Procedimento",
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
        "title": "Atendimento Academico - Guia Completo",
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
        "title": "Procedimentos Administrativos - Guia do Estudante",
        "category": "procedimentos",
        "origin": "Base de Demonstracao Academica",
        "version": "1.0-DEMO",
        "status": "active",
        "is_demo": True,
        "file_path": "knowledge_base/demo/procedimentos_administrativos.txt",
    },
    {
        "title": "Perguntas Frequentes - FAQ do Estudante",
        "category": "faq",
        "origin": "Base de Demonstracao Academica",
        "version": "1.0-DEMO",
        "status": "active",
        "is_demo": True,
        "file_path": "knowledge_base/demo/faq.txt",
    },
]


def load_file_content(relative_path: str) -> str:
    """Tenta localizar e ler o conteudo do arquivo relativo ao projeto."""
    possible_roots = [
        os.getcwd(),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
    ]
    for root in possible_roots:
        candidate = os.path.join(root, relative_path)
        if os.path.exists(candidate):
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass
    return ""


async def seed():
    """Popula o banco com dados de demonstracao evitando duplicatas."""
    print("=" * 60)
    print("FECAP Guia - Seed de DEMONSTRACAO")
    print("ATENCAO: Todos os dados sao FICTICIOS")
    print("=" * 60)

    await create_tables()
    print("[OK] Tabelas criadas/verificadas")

    async with AsyncSessionLocal() as session:
        # 1. Inserir ou atualizar Usuarios
        user_cache = {}
        for u in DEMO_USERS:
            stmt = select(User).where(User.email == u["email"])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            if not existing:
                new_user = User(
                    email=u["email"],
                    hashed_password=hash_password(u["password"]),
                    role=u["role"],
                    is_demo=u["is_demo"],
                    is_active=True,
                )
                session.add(new_user)
                await session.flush()
                user_cache[u["email"]] = new_user
                print(f"  [+] Usuario criado: {u['email']} ({u['role']})")
            else:
                user_cache[u["email"]] = existing
                print(f"  [=] Usuario existente: {u['email']}")

        # 2. Inserir ou atualizar Estudantes
        for s in DEMO_STUDENTS:
            stmt = select(Student).where(Student.email == s["email"])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            if not existing:
                user_obj = user_cache.get(s["email"])
                new_student = Student(
                    user_id=user_obj.id if user_obj else None,
                    name=s["name"],
                    ra=s["ra"],
                    course=s["course"],
                    period=s["period"],
                    email=s["email"],
                    is_demo=s["is_demo"],
                )
                session.add(new_student)
                print(f"  [+] Estudante cadastrado: {s['name']} | RA: {s['ra']}")
            else:
                print(f"  [=] Estudante existente: {s['name']}")

        # 3. Inserir ou atualizar Documentos
        for d in DEMO_DOCUMENTS:
            stmt = select(KnowledgeDocument).where(KnowledgeDocument.title == d["title"])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            content = load_file_content(d["file_path"])
            if not existing:
                new_doc = KnowledgeDocument(
                    title=d["title"],
                    category=d["category"],
                    origin=d["origin"],
                    version=d["version"],
                    status=d["status"],
                    file_path=d["file_path"],
                    content=content,
                    chunks_count=1 if content else 0,
                    is_demo=d["is_demo"],
                    published_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    created_by="Secretaria Academica",
                )
                session.add(new_doc)
                print(f"  [+] Documento indexado: {d['title']}")
            else:
                if content and not existing.content:
                    existing.content = content
                    existing.chunks_count = 1
                print(f"  [=] Documento existente: {d['title']}")

        await session.commit()
    print("")
    print("[OK] Seed concluido com sucesso no banco de dados!")


if __name__ == "__main__":
    asyncio.run(seed())
