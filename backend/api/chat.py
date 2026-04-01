"""
POST /chat — agente IA com RAG por paciente.

Fluxo:
  pergunta → busca documentos do usuário (RAG) → monta prompt → Claude → streaming SSE
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
    history = [
        {"role": m.role, "content": m.content}
        for m in request.history
    ]
    history.append({"role": "user", "content": request.message})

    try:
        system_prompt, sources = build_context_prompt(request.message, user_id)
    except Exception as e:
        logging.error("build_context_prompt failed: %s: %s", type(e).__name__, e)

        def error_stream():
            error_event = json.dumps(
                {"type": "error", "content": "Agente IA temporariamente indisponível."},
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

    def event_stream():
        # Envia as fontes como primeiro evento
        sources_event = json.dumps({"type": "sources", "sources": sources})
        yield f"data: {sources_event}\n\n"

        # Stream de tokens do LLM
        try:
            for chunk in chat_stream(system_prompt, history, sources):
                token_event = json.dumps({"type": "token", "content": chunk})
                yield f"data: {token_event}\n\n"
        except Exception as e:
            logging.error("chat_stream failed: %s: %s", type(e).__name__, e)
            error_event = json.dumps({"type": "error", "content": "Erro ao gerar resposta."})
            yield f"data: {error_event}\n\n"

        # Sinaliza fim
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
