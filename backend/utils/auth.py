"""
Autenticação — Fase 1-4: mock user local
Fase 5: substituir por validação JWT real do Supabase
"""
import os
from fastapi import Header, HTTPException


def get_current_user(authorization: str = Header(default="")) -> str:
    """
    Retorna o user_id do usuário autenticado.

    Durante o desenvolvimento (USE_MOCK_AZURE=true), retorna o MOCK_USER_ID
    definido no .env, sem validar nenhum token.

    Na Fase 5, esta função validará o JWT do Supabase e retornará o user_id real.
    """
    if os.getenv("USE_MOCK_AZURE", "true").lower() == "true":
        return os.getenv("MOCK_USER_ID", "local-dev-user-001")

    # TODO Fase 5: validar JWT Supabase
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token não fornecido")

    token = authorization.removeprefix("Bearer ")
    user_id = _validate_supabase_jwt(token)
    return user_id


def _validate_supabase_jwt(token: str) -> str:
    """Placeholder para validação real do JWT Supabase (Fase 5)."""
    raise NotImplementedError("Autenticação real será implementada na Fase 5")
