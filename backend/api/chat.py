"""
POST /chat — agente IA com RAG por paciente.

Fluxo:
  pergunta → busca documentos do usuário (RAG) → monta prompt → LLM → streaming SSE
"""
import json
import logging
import traceback

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

        def error_stream():
            debug_payload = {
                "type": "error",
                "content": "Agente IA temporariamente indisponível.",
                "debug": {
                    "stage": "build_context_prompt",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc(),
                },
            }
            yield f"data: {json.dumps(debug_payload)}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    def event_stream():
        logger.info("Starting SSE event_stream...")

        try:
            sources_event = json.dumps({"type": "sources", "sources": sources})
            yield f"data: {sources_event}\n\n"
            logger.info("Sources event sent")
        except Exception:
            logger.exception("Failed to send sources event")
            raise

        try:
            logger.info("Calling chat_stream...")
            chunk_count = 0

            for chunk in chat_stream(system_prompt, history, sources):
                chunk_count += 1
                logger.info("chat_stream chunk received | chunk_count=%s", chunk_count)

                token_event = json.dumps({"type": "token", "content": chunk})
                yield f"data: {token_event}\n\n"

            logger.info("chat_stream finished successfully | total_chunks=%s", chunk_count)

        except Exception as e:
            logger.exception("chat_stream failed")

            error_event = {
                "type": "error",
                "content": "Erro ao gerar resposta.",
                "debug": {
                    "stage": "chat_stream",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc(),
                },
            }
            yield f"data: {json.dumps(error_event)}\n\n"

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
