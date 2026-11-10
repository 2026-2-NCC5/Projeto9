"""
Router principal — agrega todos os sub-routers da API v1.
"""
from fastapi import APIRouter
from app.api.v1 import auth, student, agent, history, feedback, handoff, knowledge, dashboard, audit, documents, boletos, algebra, triage

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Autenticacao"])
api_router.include_router(student.router, prefix="/student", tags=["Estudante"])
api_router.include_router(agent.router, prefix="/agent", tags=["Agente"])
api_router.include_router(history.router, prefix="/history", tags=["Historico"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["Feedback"])
api_router.include_router(handoff.router, prefix="/handoff", tags=["Encaminhamento"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["Base de Conhecimento"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(audit.router, prefix="/audit", tags=["Auditoria"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documentos PDF (Demo)"])
api_router.include_router(boletos.router, prefix="/boletos", tags=["Segunda via de boleto (Demo)"])
api_router.include_router(algebra.router, prefix="/algebra", tags=["Álgebra Linear (Entrega 2)"])
api_router.include_router(triage.router, prefix="/triage", tags=["Triagem de Assunto (Entrega 2 IA)"])
