"""
Autenticação — Fase 5: validação real do JWT Supabase.

Com USE_MOCK_AZURE=true → retorna MOCK_USER_ID (desenvolvimento local).
Com USE_MOCK_AZURE=false → valida o JWT Bearer via cliente Supabase.
"""
import os
from fastapi import Header, HTTPException
from supabase import create_client


def get_current_user(authorization: str = Header(default="")) -> str:
    if os.getenv("USE_MOCK_AZURE", "true").lower() == "true":
        return os.getenv("MOCK_USER_ID", "local-dev-user-001")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token não fornecido.")

    token = authorization.removeprefix("Bearer ")
    return _validate_supabase_jwt(token)


def _validate_supabase_jwt(token: str) -> str:
    """
    Valida o JWT via Supabase client (get_user), evitando problemas
    de algoritmo/versão do PyJWT. Retorna o user_id (sub).
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        raise HTTPException(
            status_code=500,
            detail="SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY não configurados.",
        )

    try:
        supabase = create_client(url, key)
        response = supabase.auth.get_user(token)
        if not response.user:
            raise HTTPException(status_code=401, detail="Token inválido.")
        return response.user.id
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Erro ao validar token: {e}")
