"""
POST /chat — agente IA com RAG por paciente.

MODO DEBUG TEMPORÁRIO:
- Desabilita SSE temporariamente
- Retorna JSONResponse com erro detalhado
- Facilita diagnosticar falhas em build_context_prompt e chat_stream
"""
import logging
import traceback

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from models.chat import ChatRequest
from services.rag.retriever import build_context_prompt
from services.azure.llm import chat_stream
from utils.auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/chat")
def chat(
    request: ChatRequest,
    user_id: str = Depends(get_current_user),
):
    logger.info("POST /chat called | user_id=%s", user_id)

    history = [
        {"role": m.role, "content": m.content}
        for m in request.history
    ]
    history.append({"role": "user", "content": request.message})

    logger.info(
        "Chat request prepared | history_len=%s | message_len=%s",
        len(history),
        len(request.message or ""),
    )

    try:
        logger.info("Calling build_context_prompt...")
        system_prompt, sources = build_context_prompt(request.message, user_id)
        logger.info(
            "build_context_prompt succeeded | sources_count=%s | sources=%s | system_prompt_len=%s",
            len(sources) if sources else 0,
            sources,
            len(system_prompt or ""),
        )
    except Exception as e:
        logger.exception("build_context_prompt failed")
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "stage": "build_context_prompt",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc(),
            },
        )

    try:
        logger.info("Calling chat_stream in debug non-stream mode...")

        full_text = ""
        chunk_count = 0

        for chunk in chat_stream(system_prompt, history, sources):
            chunk_count += 1
            full_text += chunk

        logger.info(
            "chat_stream finished successfully | chunk_count=%s | response_len=%s",
            chunk_count,
            len(full_text),
        )

        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                "stage": "done",
                "sources": sources,
                "response": full_text,
                "chunk_count": chunk_count,
            },
        )

    except Exception as e:
        logger.exception("chat_stream failed")
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "stage": "chat_stream",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc(),
            },
        )
