"""
Endpoints públicos de emergência — sem autenticação.

GET /emergency/{user_id}        → perfil JSON
GET /emergency/{user_id}/qr     → QR Code PNG
GET /emergency/{user_id}/pdf    → cartão imprimível PDF
"""
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from models.emergency import EmergencyProfile
from services.emergency import build_emergency_profile
from services.qr_generator import generate_qr_png
from services.pdf_generator import generate_emergency_pdf

router = APIRouter()

APP_URL = os.getenv("NEXT_PUBLIC_APP_URL", "http://localhost:3000")


def _get_profile_or_404(user_id: str) -> EmergencyProfile:
    profile = build_emergency_profile(user_id)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Perfil de emergência não encontrado. Nenhum documento médico foi enviado para este usuário.",
        )
    return profile


@router.get("/emergency/{user_id}", response_model=EmergencyProfile)
def get_emergency_profile(user_id: str):
    """Retorna o perfil de emergência em JSON. Endpoint público, sem login."""
    return _get_profile_or_404(user_id)


@router.get("/emergency/{user_id}/qr")
def get_emergency_qr(user_id: str):
    """Gera e retorna o QR Code PNG apontando para a página de emergência."""
    _get_profile_or_404(user_id)
    url = f"{APP_URL}/emergency/{user_id}"
    png_bytes = generate_qr_png(url)
    return Response(content=png_bytes, media_type="image/png")


@router.get("/emergency/{user_id}/pdf")
def get_emergency_pdf(user_id: str):
    """Gera e retorna o cartão de emergência em PDF (A5, imprimível)."""
    profile = _get_profile_or_404(user_id)
    url = f"{APP_URL}/emergency/{user_id}"
    qr_bytes = generate_qr_png(url, box_size=6, border=2)
    pdf_bytes = generate_emergency_pdf(profile, qr_bytes)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="emergencia_{user_id}.pdf"'},
    )
