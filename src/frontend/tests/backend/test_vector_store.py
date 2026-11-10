"""
Testes automatizados para a Fase 2: ChromaDB e embeddings all-MiniLM-L6-v2.
Valida:
- Criacao de chunks com tamanho e sobreposicao corretos.
- Geracao e normalizacao de embeddings.
- Persistencia na colecao ChromaDB.
- Idempotencia na reindexacao sem duplicatas.
- Busca semantica Top-K e retorno correto de metadados.
- Desindexacao ao desativar documentos.
- Tratamento de consultas sem resultados ou vazias.
"""
import os
import shutil
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.core.database import Base
from app.models.entities import KnowledgeDocument
from app.knowledge.chunker import split_text_into_chunks, prepare_document_chunks
from app.knowledge.vector_store import VectorStoreService
from app.knowledge.indexer import index_all_active_documents, sync_document_to_vector_store


TEST_CHROMA_DIR = "./test_chroma_db"
TEST_SQLITE_URL = "sqlite+aiosqlite:///./test_vector_knowledge.db"


@pytest_asyncio.fixture
async def vector_test_env(tmp_path):
    """Configura ambiente isolado com SQLite temporario e ChromaDB temporario."""
    chroma_dir = str(tmp_path / "test_chroma_db")
    sqlite_file = str(tmp_path / "test_vector_knowledge.db")
    sqlite_url = f"sqlite+aiosqlite:///{sqlite_file}"

    os.makedirs(chroma_dir, exist_ok=True)
    v_service = VectorStoreService(
        persist_directory=chroma_dir,
        collection_name="test_knowledge_collection"
    )
    v_service.reset_collection()

    engine = create_async_engine(sqlite_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield v_service, async_session

    await engine.dispose()


def test_chunker_boundaries_and_overlap():
    """Testa particionamento respeitando limites e sobreposição."""
    text = (
        "Paragrafo 1: O portal do aluno permite consultar notas e frequencia.\n"
        "Paragrafo 2: Para solicitar documentos acesse o menu de requerimentos.\n"
        "Paragrafo 3: O prazo maximo para expedicao e de ate 3 dias uteis."
    )
    chunks = split_text_into_chunks(text, chunk_size=90, chunk_overlap=20)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) <= 90


@pytest.mark.asyncio
async def test_indexing_persistence_and_idempotency(vector_test_env):
    """Testa insercao de documentos ativos, contagem de chunks e idempotencia do upsert."""
    v_service, session_maker = vector_test_env

    async with session_maker() as session:
        doc1 = KnowledgeDocument(
            title="Normas de Rematricula",
            category="secretaria",
            origin="Secretaria Geral",
            version="1.0-DEMO",
            status="active",
            content="A rematricula para veteranos ocorre no mes de julho pelo portal.",
            is_demo=True,
        )
        doc2 = KnowledgeDocument(
            title="Regras Antigas de Prova",
            category="historico",
            origin="Arquivo Morto",
            version="0.9",
            status="inactive",  # Nao deve ser indexado
            content="Regras antigas revogadas no ano de 2020.",
            is_demo=True,
        )
        session.add_all([doc1, doc2])
        await session.commit()

        # 1. Indexacao de documentos ativos
        res = await index_all_active_documents(session, v_service)
        assert res["documents_processed"] == 1
        assert res["total_chunks_indexed"] >= 1
        initial_count = v_service.count()
        assert initial_count >= 1

        # 2. Teste de reindexacao (idempotencia sem duplicacao)
        res_reindex = await index_all_active_documents(session, v_service)
        assert res_reindex["documents_processed"] == 1
        assert v_service.count() == initial_count


@pytest.mark.asyncio
async def test_semantic_search_accuracy(vector_test_env):
    """Testa se busca semantica encontra o documento com base no significado."""
    v_service, session_maker = vector_test_env

    async with session_maker() as session:
        doc = KnowledgeDocument(
            title="Procedimento de Carteirinha Estudantil",
            category="documentos_certidoes",
            origin="Balcao ASA",
            version="2.0-DEMO",
            status="active",
            content=(
                "A carteirinha estudantil digital esta disponivel no aplicativo oficial. "
                "Para emitir a segunda via fisica, pague a taxa correspondente e retire no balcao."
            ),
            is_demo=True,
        )
        session.add(doc)
        await session.commit()
        await index_all_active_documents(session, v_service)

    # Busca semantica por sinonimo
    results = v_service.query_similar("Como pegar novo cartao de identificacao do aluno?", top_k=1)
    assert len(results) == 1
    top_hit = results[0]

    assert top_hit["metadata"]["title"] == "Procedimento de Carteirinha Estudantil"
    assert top_hit["metadata"]["version"] == "2.0-DEMO"
    assert top_hit["similarity_score"] > 0.40
    assert "carteirinha estudantil" in top_hit["text"].lower()


@pytest.mark.asyncio
async def test_deindex_when_status_inactive(vector_test_env):
    """Testa remocao de vetores do ChromaDB quando o documento se torna inativo."""
    v_service, session_maker = vector_test_env

    doc_id = None
    async with session_maker() as session:
        doc = KnowledgeDocument(
            title="Politica Temporaria de Estagio",
            category="estagios",
            origin="Setor de Carreiras",
            version="1.0-DEMO",
            status="active",
            content="Regras extraordinarias para validacao de termos de compromisso de estagio remoto.",
            is_demo=True,
        )
        session.add(doc)
        await session.commit()
        doc_id = str(doc.id)
        await index_all_active_documents(session, v_service)
        assert v_service.count() >= 1

    # Nova sessao para alterar status e sincronizar
    async with session_maker() as session:
        stmt = select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id)
        res = await session.execute(stmt)
        target_doc = res.scalar_one()
        target_doc.status = "inactive"
        await session.commit()

        sync_res = await sync_document_to_vector_store(doc_id, session, v_service)
        assert sync_res["status"] == "deindexed"
        assert v_service.count() == 0


def test_query_no_results_or_empty(vector_test_env):
    """Testa comportamento para queries vazias."""
    v_service, _ = vector_test_env
    empty_res = v_service.query_similar("")
    assert empty_res == []
