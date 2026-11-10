"""
Router de Base de Conhecimento (Knowledge) — Fase 6.
Gerencia listagem, cadastro, edição, versionamento, ativação/desativação,
upload de arquivos PDF/TXT e sincronização automática com o ChromaDB.
Restrito a administradores (RBAC).
"""
import base64
from email.parser import BytesParser
from email.policy import default as default_email_policy
import io
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import record_audit_log, require_admin
from app.knowledge.indexer import sync_document_to_vector_store
from app.models.entities import KnowledgeDocument, User
from app.schemas.schemas import (
    KnowledgeDocumentCreate,
    KnowledgeDocumentDetailResponse,
    KnowledgeDocumentResponse,
    KnowledgeDocumentUpdate,
)

router = APIRouter()


def extract_text_from_file(filename: str, raw_bytes: bytes) -> str:
    """Extrai e valida conteúdo textual de arquivos TXT ou PDF."""
    max_bytes = settings.max_document_size_mb * 1024 * 1024
    if len(raw_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Arquivo excede o limite de {settings.max_document_size_mb} MB.",
        )

    lower_name = filename.lower()
    if lower_name.endswith(".txt"):
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = raw_bytes.decode("latin-1", errors="ignore")
    elif lower_name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(raw_bytes))
            pages_text = [page.extract_text() or "" for page in reader.pages]
            text = "\n\n".join(pages_text)
        except ImportError:
            # Fallback para extração de texto legível em streams PDF simples
            text = raw_bytes.decode("latin-1", errors="ignore")
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Não foi possível extrair texto do PDF: {str(exc)}",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato não suportado. Envie apenas arquivos .pdf ou .txt.",
        )

    cleaned = text.strip()
    if len(cleaned) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo enviado está vazio ou não possui texto extraível suficiente.",
        )
    return cleaned


def _parse_multipart_body(content_type: str, body: bytes) -> dict:
    """Faz parse nativo de multipart/form-data usando a biblioteca padrão email.parser."""
    header_bytes = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8")
    msg = BytesParser(policy=default_email_policy).parsebytes(header_bytes + body)
    parsed: dict = {}
    if msg.is_multipart():
        for part in msg.iter_parts():
            name = part.get_param("name", header="content-disposition")
            filename = part.get_filename()
            payload = part.get_payload(decode=True) or b""
            if filename:
                parsed["filename"] = filename
                parsed["file_bytes"] = payload
            elif name:
                parsed[name] = payload.decode("utf-8", errors="ignore").strip()
    return parsed


@router.get("/", response_model=List[KnowledgeDocumentResponse], status_code=status.HTTP_200_OK)
async def list_documents(
    status_filter: Optional[str] = None,
    category: Optional[str] = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> List[KnowledgeDocumentResponse]:
    """Lista todos os documentos da base de conhecimento (exclusivo admin)."""
    stmt = select(KnowledgeDocument).order_by(KnowledgeDocument.updated_at.desc())
    if status_filter:
        stmt = stmt.where(KnowledgeDocument.status == status_filter)
    if category:
        stmt = stmt.where(KnowledgeDocument.category == category)

    res = await db.execute(stmt)
    docs = res.scalars().all()
    return [KnowledgeDocumentResponse.model_validate(d) for d in docs]


@router.get("/{doc_id}", response_model=KnowledgeDocumentDetailResponse, status_code=status.HTTP_200_OK)
async def get_document(
    doc_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeDocumentDetailResponse:
    """Retorna os detalhes e o conteúdo completo de um documento."""
    stmt = select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado.",
        )
    return KnowledgeDocumentDetailResponse.model_validate(doc)


@router.post("/", response_model=KnowledgeDocumentDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: KnowledgeDocumentCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeDocumentDetailResponse:
    """Cadastra novo documento orientativo, indexa no ChromaDB se ativo e registra auditoria."""
    if not payload.content or len(payload.content.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O conteúdo do documento deve ter pelo menos 10 caracteres.",
        )

    doc = KnowledgeDocument(
        title=payload.title.strip(),
        category=payload.category,
        origin=payload.origin or "Secretaria Acadêmica (Admin)",
        version=payload.version or "1.0",
        status=payload.status or "active",
        content=payload.content.strip(),
        file_path=payload.file_path,
        is_demo=payload.is_demo,
        created_by=admin.email,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Sincroniza com ChromaDB (indexa se active, remove se inactive)
    await sync_document_to_vector_store(doc.id, db)
    await db.refresh(doc)

    await record_audit_log(
        db=db,
        action="knowledge_created",
        resource="knowledge_document",
        detail=f"Documento '{doc.title}' (v{doc.version}, status={doc.status}, chunks={doc.chunks_count}) criado",
        user_id=admin.id,
    )

    return KnowledgeDocumentDetailResponse.model_validate(doc)


@router.post("/upload", response_model=KnowledgeDocumentDetailResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeDocumentDetailResponse:
    """
    Realiza upload autorizado de arquivo PDF ou TXT (via multipart/form-data ou JSON base64),
    extrai texto e sincroniza com o ChromaDB.
    """
    content_type = request.headers.get("content-type", "")
    raw_body = await request.body()

    if "multipart/form-data" in content_type:
        parsed = _parse_multipart_body(content_type, raw_body)
        filename = parsed.get("filename", "documento.txt")
        file_bytes = parsed.get("file_bytes", b"")
        title = parsed.get("title")
        category = parsed.get("category", "documentos_certidoes")
        origin = parsed.get("origin", "Upload Administrativo")
        version = parsed.get("version", "1.0")
        status_val = parsed.get("status", "active")
    else:
        data = await request.json()
        filename = data.get("filename", "documento.txt")
        if "file_base64" in data:
            file_bytes = base64.b64decode(data["file_base64"])
        elif "content" in data:
            file_bytes = str(data["content"]).encode("utf-8")
        else:
            file_bytes = b""
        title = data.get("title")
        category = data.get("category", "documentos_certidoes")
        origin = data.get("origin", "Upload Administrativo")
        version = data.get("version", "1.0")
        status_val = data.get("status", "active")

    extracted_content = extract_text_from_file(filename, file_bytes)
    doc_title = (title or filename.rsplit(".", 1)[0]).strip()

    doc = KnowledgeDocument(
        title=doc_title,
        category=category,
        origin=origin,
        version=version,
        status=status_val,
        file_path=filename,
        content=extracted_content,
        is_demo=False,
        created_by=admin.email,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    await sync_document_to_vector_store(doc.id, db)
    await db.refresh(doc)

    await record_audit_log(
        db=db,
        action="knowledge_uploaded",
        resource="knowledge_document",
        detail=f"Upload '{filename}' -> '{doc.title}' (v{doc.version}, chunks={doc.chunks_count})",
        user_id=admin.id,
    )

    return KnowledgeDocumentDetailResponse.model_validate(doc)



@router.put("/{doc_id}", response_model=KnowledgeDocumentDetailResponse, status_code=status.HTTP_200_OK)
async def update_document(
    doc_id: str,
    payload: KnowledgeDocumentUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeDocumentDetailResponse:
    """Atualiza documento existente, incrementa/mantém versão e re-sincroniza no ChromaDB sem duplicar."""
    stmt = select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado.",
        )

    if payload.title is not None:
        doc.title = payload.title.strip()
    if payload.category is not None:
        doc.category = payload.category
    if payload.origin is not None:
        doc.origin = payload.origin
    if payload.version is not None:
        doc.version = payload.version
    if payload.status is not None:
        if payload.status not in ("active", "inactive", "draft"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status inválido. Use active, inactive ou draft.",
            )
        doc.status = payload.status
    if payload.content is not None:
        if len(payload.content.strip()) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O conteúdo do documento deve ter pelo menos 10 caracteres.",
            )
        doc.content = payload.content.strip()

    await db.commit()
    await db.refresh(doc)

    sync_res = await sync_document_to_vector_store(doc.id, db)
    await db.refresh(doc)

    await record_audit_log(
        db=db,
        action="knowledge_updated",
        resource="knowledge_document",
        detail=f"Documento '{doc.title}' atualizado (v{doc.version}, status={doc.status}, sync={sync_res.get('status')})",
        user_id=admin.id,
    )

    return KnowledgeDocumentDetailResponse.model_validate(doc)


@router.patch("/{doc_id}/status", response_model=KnowledgeDocumentDetailResponse, status_code=status.HTTP_200_OK)
async def toggle_document_status(
    doc_id: str,
    new_status: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeDocumentDetailResponse:
    """Ativa ou desativa um documento, atualizando imediatamente a coleção do ChromaDB."""
    if new_status not in ("active", "inactive", "draft"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status inválido. Use active, inactive ou draft.",
        )

    stmt = select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado.",
        )

    doc.status = new_status
    await db.commit()
    await db.refresh(doc)

    sync_res = await sync_document_to_vector_store(doc.id, db)
    await db.refresh(doc)

    await record_audit_log(
        db=db,
        action="knowledge_status_changed",
        resource="knowledge_document",
        detail=f"Status de '{doc.title}' alterado para {new_status} ({sync_res.get('status')})",
        user_id=admin.id,
    )

    return KnowledgeDocumentDetailResponse.model_validate(doc)
