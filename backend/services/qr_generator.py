"""
Geração de QR Code para a página de emergência do paciente.
Usa a biblioteca qrcode[pil] — sem dependência Azure.
"""
import io
import qrcode
from qrcode.image.pure import PyPNGImage


def generate_qr_png(url: str, box_size: int = 8, border: int = 3) -> bytes:
    """
    Gera um QR Code PNG apontando para a URL informada.
    Retorna os bytes do arquivo PNG.
    """
    qr = qrcode.QRCode(
        version=None,          # tamanho automático
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(image_factory=PyPNGImage)
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue()
