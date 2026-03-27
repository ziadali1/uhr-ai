"""
Geração do cartão de emergência em PDF usando ReportLab.
Produz um cartão A5 imprimível com as informações críticas do paciente.
"""
import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as rl_canvas

from models.emergency import EmergencyProfile

# Paleta
RED = colors.HexColor("#DC2626")
RED_LIGHT = colors.HexColor("#FEE2E2")
GRAY_DARK = colors.HexColor("#111827")
GRAY = colors.HexColor("#6B7280")
GRAY_LIGHT = colors.HexColor("#F9FAFB")
WHITE = colors.white
YELLOW = colors.HexColor("#FEF3C7")
YELLOW_BORDER = colors.HexColor("#F59E0B")
GREEN = colors.HexColor("#059669")


def generate_emergency_pdf(profile: EmergencyProfile, qr_png_bytes: bytes) -> bytes:
    """
    Gera o PDF do cartão de emergência.
    Retorna os bytes do arquivo PDF.
    """
    buf = io.BytesIO()
    w, h = A5  # 148 x 210 mm
    c = rl_canvas.Canvas(buf, pagesize=A5)

    _draw_header(c, w, h)
    y = _draw_blood_type(c, w, h, profile.blood_type)
    y = _draw_allergies(c, w, y, profile.allergies)
    y = _draw_medications(c, w, y, profile.active_medications)
    y = _draw_conditions(c, w, y, profile.active_conditions)
    _draw_qr_and_footer(c, w, y, qr_png_bytes, profile.last_updated)

    c.save()
    return buf.getvalue()


def _draw_header(c: rl_canvas.Canvas, w: float, h: float) -> None:
    # Fundo vermelho no topo
    c.setFillColor(RED)
    c.rect(0, h - 28 * mm, w, 28 * mm, fill=True, stroke=False)

    # Título
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(w / 2, h - 12 * mm, "🚨  EMERGÊNCIA  🚨")

    c.setFont("Helvetica", 9)
    c.drawCentredString(w / 2, h - 20 * mm, "Unified Health Record — Informações Médicas Críticas")


def _draw_blood_type(c: rl_canvas.Canvas, w: float, h: float, blood_type: str | None) -> float:
    y = h - 38 * mm
    if blood_type:
        c.setFillColor(RED_LIGHT)
        c.setStrokeColor(RED)
        c.setLineWidth(1)
        c.roundRect(10 * mm, y - 10 * mm, w - 20 * mm, 12 * mm, 3 * mm, fill=True, stroke=True)

        c.setFillColor(RED)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(14 * mm, y - 5 * mm, f"🩸  Tipo Sanguíneo: {blood_type}")
    return y - 14 * mm


def _draw_section_title(c: rl_canvas.Canvas, title: str, y: float, x: float = 10) -> float:
    c.setFillColor(GRAY_DARK)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x * mm, y, title)
    c.setStrokeColor(GRAY)
    c.setLineWidth(0.3)
    c.line(x * mm, y - 1 * mm, (x + 50) * mm, y - 1 * mm)
    return y - 5 * mm


def _draw_allergies(c: rl_canvas.Canvas, w: float, y: float, allergies) -> float:
    if not allergies:
        return y
    y = _draw_section_title(c, "⚠️  ALERGIAS", y)
    for allergy in allergies:
        color = RED if allergy.severity == "severa" else GRAY_DARK
        c.setFillColor(color)
        c.setFont("Helvetica-Bold" if allergy.severity == "severa" else "Helvetica", 9)
        severity_tag = f"  [{allergy.severity.upper()}]" if allergy.severity == "severa" else ""
        c.drawString(14 * mm, y, f"•  {allergy.name}{severity_tag}")
        y -= 5 * mm
    return y - 2 * mm


def _draw_medications(c: rl_canvas.Canvas, w: float, y: float, medications) -> float:
    if not medications:
        return y
    y = _draw_section_title(c, "💊  MEDICAMENTOS EM USO", y)
    for med in medications:
        c.setFillColor(GRAY_DARK)
        c.setFont("Helvetica", 9)
        c.drawString(14 * mm, y, f"•  {med.name} {med.dose}")
        if med.alert:
            y -= 4 * mm
            c.setFillColor(YELLOW_BORDER)
            c.setFont("Helvetica-Oblique", 8)
            c.drawString(18 * mm, y, f"⚠  {med.alert}")
        y -= 5 * mm
    return y - 2 * mm


def _draw_conditions(c: rl_canvas.Canvas, w: float, y: float, conditions: list[str]) -> float:
    if not conditions:
        return y
    y = _draw_section_title(c, "🏥  CONDIÇÕES ATIVAS", y)
    for cond in conditions:
        c.setFillColor(GRAY_DARK)
        c.setFont("Helvetica", 9)
        c.drawString(14 * mm, y, f"•  {cond}")
        y -= 5 * mm
    return y - 2 * mm


def _draw_qr_and_footer(
    c: rl_canvas.Canvas,
    w: float,
    y: float,
    qr_png_bytes: bytes,
    last_updated: datetime,
) -> None:
    # QR Code
    qr_size = 28 * mm
    qr_x = w - qr_size - 10 * mm
    qr_y = 14 * mm

    qr_buf = ImageReader(io.BytesIO(qr_png_bytes))
    c.drawImage(qr_buf, qr_x, qr_y, width=qr_size, height=qr_size)

    c.setFillColor(GRAY)
    c.setFont("Helvetica", 7)
    c.drawCentredString(qr_x + qr_size / 2, qr_y - 4 * mm, "Escanear para")
    c.drawCentredString(qr_x + qr_size / 2, qr_y - 7.5 * mm, "histórico completo")

    # Linha divisória
    c.setStrokeColor(GRAY)
    c.setLineWidth(0.3)
    c.line(10 * mm, 12 * mm, w - 10 * mm, 12 * mm)

    # Rodapé
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 7)
    updated_str = last_updated.strftime("%d/%m/%Y %H:%M") if last_updated else "—"
    c.drawString(10 * mm, 8 * mm, f"Atualizado em: {updated_str}")
    c.drawRightString(w - 10 * mm, 8 * mm, "Unified Health Record")
    c.drawString(10 * mm, 4 * mm, "⚕  Informações para uso exclusivo em emergências médicas.")
