"""
UHR — Unified Health Record | FastAPI Entry Point

Para rodar localmente:
    uvicorn main:app --reload

Documentação interativa: http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.upload import router as upload_router
from api.documents import router as documents_router
from api.chat import router as chat_router
from api.analysis import router as analysis_router
from api.emergency import router as emergency_router
from api.health_profile import router as health_router

app = FastAPI(
    title="UHR — Unified Health Record",
    description="API para centralização e análise de históricos médicos com Azure AI",
    version="0.5.0",
)

import os

_allowed_origins = [
    "http://localhost:3000",
]
_prod_url = os.getenv("FRONTEND_URL")
if _prod_url:
    _allowed_origins.append(_prod_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router, tags=["Documentos"])
app.include_router(documents_router, tags=["Documentos"])
app.include_router(chat_router, tags=["Agente IA"])
app.include_router(analysis_router, tags=["Análise"])
app.include_router(emergency_router, tags=["Emergência"])
app.include_router(health_router, tags=["Saúde Manual"])


@app.get("/health", tags=["Sistema"])
def health_check():
    return {"status": "ok", "version": "0.5.0", "phase": 5}
