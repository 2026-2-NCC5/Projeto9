"""
Router principal — agrega todos os sub-routers da API v1.
"""
from fastapi import APIRouter
from app.api.v1 import auth, student, agent, history, feedback, handoff, knowledge, dashboard, audit

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
