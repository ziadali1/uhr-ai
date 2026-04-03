"""
POST /chat — agente IA com RAG por paciente.

Fluxo:
  pergunta → busca documentos do usuário (RAG) → monta prompt → LLM → streaming SSE
"""
import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

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

    try:
        logger.info("Calling build_context_prompt...")
        system_prompt, sources = build_context_prompt(request.message, user_id)
        logger.info(
            "build_context_prompt succeeded | sources_count=%s | system_prompt_len=%s",
            len(sources) if sources else 0,
            len(system_prompt or ""),
        )
    except Exception:
        logger.exception("build_context_prompt failed")

        def error_stream():
            error_event = json.dumps(
                {"type": "error", "content": "Agente IA temporariamente indisponível."}
            )
            yield f"data: {error_event}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

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

    def event_stream():
        logger.info("Starting SSE event_stream...")

        try:
            # Envia as fontes como primeiro evento
            sources_event = json.dumps({"type": "sources", "sources": sources})
            yield f"data: {sources_event}\n\n"
            logger.info("Sources event sent")

            # Stream de tokens do LLM
            chunk_count = 0
            for chunk in chat_stream(system_prompt, history, sources):
                chunk_count += 1
                token_event = json.dumps({"type": "token", "content": chunk})
                yield f"data: {token_event}\n\n"

            logger.info("chat_stream finished successfully | total_chunks=%s", chunk_count)

        except Exception:
            logger.exception("chat_stream failed")
            error_event = json.dumps(
                {"type": "error", "content": "Erro ao gerar resposta."}
            )
            yield f"data: {error_event}\n\n"

        # Sinaliza fim
        logger.info("Sending done event")
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
