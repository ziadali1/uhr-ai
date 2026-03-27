"""
POST /chat — agente IA com RAG por paciente.

Fluxo:
  pergunta → busca documentos do usuário (RAG) → monta prompt → Claude → streaming SSE
"""
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from models.chat import ChatRequest
from services.rag.retriever import build_context_prompt
from services.azure.llm import chat_stream
from utils.auth import get_current_user

router = APIRouter()


@router.post("/chat")
def chat(
    request: ChatRequest,
    user_id: str = Depends(get_current_user),
):
    system_prompt, sources = build_context_prompt(request.message, user_id)

    history = [
        {"role": m.role, "content": m.content}
        for m in request.history
    ]
    history.append({"role": "user", "content": request.message})

    def event_stream():
        # Envia as fontes como primeiro evento
        sources_event = json.dumps({"type": "sources", "sources": sources})
        yield f"data: {sources_event}\n\n"

        # Stream de tokens do LLM
        for chunk in chat_stream(system_prompt, history, sources):
            token_event = json.dumps({"type": "token", "content": chunk})
            yield f"data: {token_event}\n\n"

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
