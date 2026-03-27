"""
Autenticação — Fase 5: validação real do JWT Supabase.

Com USE_MOCK_AZURE=true → retorna MOCK_USER_ID (desenvolvimento local).
Com USE_MOCK_AZURE=false → valida o JWT Bearer enviado pelo frontend.
"""
import os
import jwt
from fastapi import Header, HTTPException


def get_current_user(authorization: str = Header(default="")) -> str:
    if os.getenv("USE_MOCK_AZURE", "true").lower() == "true":
        return os.getenv("MOCK_USER_ID", "local-dev-user-001")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token não fornecido.")

    token = authorization.removeprefix("Bearer ")
    return _validate_supabase_jwt(token)


def _validate_supabase_jwt(token: str) -> str:
    """
    Valida o JWT emitido pelo Supabase e retorna o user_id (sub).
    O JWT_SECRET está em: Supabase Dashboard → Settings → API → JWT Secret.
    """
    secret = os.environ.get("SUPABASE_JWT_SECRET")
    if not secret:
        raise HTTPException(
            status_code=500,
            detail="SUPABASE_JWT_SECRET não configurado no servidor.",
        )

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        user_id: str = payload["sub"]
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado.")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Token inválido: {e}")
