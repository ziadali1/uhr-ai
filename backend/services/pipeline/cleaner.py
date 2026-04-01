"""
Document cleaner — separates clinical content from administrative metadata.

Strategy:
  1. Regex patterns for known admin data (CPF, CNPJ, CRM, addresses, phones)
  2. Line-level scoring: lines dominated by admin signals are isolated
  3. Section-based removal for known boilerplate blocks
  4. Returns (clinical_text, admin_metadata) — no data is discarded, just classified

This does NOT use a blocklist of medical terms. It targets structural/contextual
patterns that indicate administrative origin regardless of document layout.
"""

import re
from typing import NamedTuple


class CleanResult(NamedTuple):
    clinical_text: str
    admin_metadata: dict


# ── Admin detection patterns ──────────────────────────────────────────────────

_ADMIN_LINE_PATTERNS = [
    # Document IDs / registration numbers
    r"\bcpf\s*[:.]?\s*\d{3}[\.\-]?\d{3}[\.\-]?\d{3}[\-]?\d{2}",
    r"\bcnpj\s*[:.]?\s*\d{2}[\.\-]?\d{3}[\.\-]?\d{3}[/\-]?\d{4}[\-]?\d{2}",
    r"\brg\s*[:.]?\s*[\d\.\-x]+",
    r"\bcrm\s*[:.]?\s*[\d\.\-]+",
    r"\bcrf\s*[:.]?\s*[\d\.\-]+",
    r"\bcnes\s*[:.]?\s*\d+",
    r"\breq(?:uisiç[aã]o)?\s*(?:n[oº°]?)?\s*[:.]?\s*[\d\.\-/]+",
    r"\bprotocolo\s*[:.]?\s*[\d\.\-/]+",
    # Contact info
    r"\btel(?:efone)?\s*[:.]?\s*\(?\d{2}\)?\s*[\d\s\-]{7,}",
    r"\bfax\s*[:.]?\s*\(?\d{2}\)?\s*[\d\s\-]{7,}",
    r"@\w+\.\w{2,}",                   # email
    r"\bwww\.\w+\.\w{2,}",             # website
    r"\bhttp[s]?://",
    # Address patterns
    r"\brua\s+\w",
    r"\bav(?:enida)?\s+\w",
    r"\bbairo\s+\w",
    r"\bbairro\s+\w",
    r"\bcep\s*[:.]?\s*\d{5}[\-]?\d{3}",
    r"\bestado\s*[:.]?\s*[a-z]{2}",
    # Insurance / convenio
    r"\bconv[eê]nio\s*[:.]",
    r"\bplano\s*[:.]",
    r"\bmatrícula\s*[:.]",
    # Auth / signature block
    r"\bassina(?:tura|do)\s+eletron",
    r"\bchave\s+de\s+verifica[çc][aã]o",
    r"\bautentici[dt]",
    r"\bvalide\s+em",
    r"\brespons[aá]vel\s+t[eé]cnico",
    # Generic admin labels
    r"\bdata\s*(?:de\s*)?emiss[aã]o\s*[:.]",
    r"\bdata\s*(?:de\s*)?impress[aã]o\s*[:.]",
    r"\bdata\s*(?:de\s*)?solicita[çc][aã]o\s*[:.]",
    r"\bm[eé]dico\s+solicitante\s*[:.]",
    r"\bunidade\s*[:.]",
    r"\bmatriz\s*[:.]",
    r"\bsetor\s*[:.]",
    r"\bregistro\s+no\s+crm",
    # Page markers
    r"\bp[aá]g(?:ina)?\s*[:.]?\s*\d+",
    r"\bpágina\s+\d+",
]

_COMPILED_ADMIN = [re.compile(p, re.IGNORECASE) for p in _ADMIN_LINE_PATTERNS]

# Section-level boilerplate blocks (multi-line patterns to strip entirely)
_BOILERPLATE_BLOCKS = [
    # Lab footer/signature block
    re.compile(
        r"(?:este\s+laudo\s+foi\s+(?:assinado|emitido)|assinatura\s+eletr[oô]nica|"
        r"documento\s+gerado\s+por|valide\s+este\s+documento).{0,500}",
        re.IGNORECASE | re.DOTALL,
    ),
    # Address block (3+ consecutive address-like lines)
    re.compile(
        r"(?:(?:rua|av(?:enida)?|alameda|travessa)\s+[^\n]+\n){2,}",
        re.IGNORECASE,
    ),
]


def _is_admin_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    return any(p.search(stripped) for p in _COMPILED_ADMIN)


def _extract_cpf(text: str) -> str | None:
    m = re.search(r"\d{3}[\.\-]?\d{3}[\.\-]?\d{3}[\-]?\d{2}", text)
    return m.group() if m else None


def _extract_crm(text: str) -> str | None:
    m = re.search(r"\bcrm\s*[:.]?\s*([\d\.\-]+(?:/[a-z]{2})?)", text, re.IGNORECASE)
    return m.group(1) if m else None


def _extract_cnes(text: str) -> str | None:
    m = re.search(r"\bcnes\s*[:.]?\s*(\d+)", text, re.IGNORECASE)
    return m.group(1) if m else None


def clean(raw_text: str) -> CleanResult:
    """
    Split raw OCR text into clinical content and admin metadata.

    Returns:
        clinical_text  — text suitable for clinical extraction
        admin_metadata — dict with extracted admin fields (cpf, crm, cnes, etc.)
    """
    # Step 1: strip boilerplate blocks
    working = raw_text
    for pattern in _BOILERPLATE_BLOCKS:
        working = pattern.sub("", working)

    # Step 2: line-level classification
    lines = working.splitlines()
    clinical_lines: list[str] = []
    admin_lines: list[str] = []

    for line in lines:
        if _is_admin_line(line):
            admin_lines.append(line)
        else:
            clinical_lines.append(line)

    clinical_text = "\n".join(clinical_lines).strip()

    # Step 3: extract structured admin fields from original text
    admin_metadata: dict = {
        "cpf": _extract_cpf(raw_text),
        "crm": _extract_crm(raw_text),
        "cnes": _extract_cnes(raw_text),
        "admin_lines": [l.strip() for l in admin_lines if l.strip()],
    }
    # Remove None values
    admin_metadata = {k: v for k, v in admin_metadata.items() if v}

    return CleanResult(clinical_text=clinical_text, admin_metadata=admin_metadata)
