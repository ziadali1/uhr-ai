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

app = FastAPI(
    title="UHR — Unified Health Record",
    description="API para centralização e análise de históricos médicos com Azure AI",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router, tags=["Documentos"])
app.include_router(documents_router, tags=["Documentos"])


@app.get("/health", tags=["Sistema"])
def health_check():
    return {"status": "ok", "version": "0.1.0", "phase": 1}
