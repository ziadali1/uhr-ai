"""
Query Router — LLM-driven intent classification, entity extraction, SQL dispatch.

RETRIEVE-04: routes aggregation/numeric queries to SQL, narrative queries to hybrid search.
"""
import json
import logging
import os
import re
from datetime import date
from typing import Literal

from pydantic import BaseModel

from services.azure.llm import generate_json
from services.azure.search import search, SearchResult
from services.azure.embeddings import generate_embedding
from services.supabase_store import _get_client
from models.document import (
    StructuredResult,
    StructuredLab,
    ImagingReport,
    ClinicalNote,
    MedicationDocument,
)

logger = logging.getLogger(__name__)

# ── Mock guard ────────────────────────────────────────────────────────────────

_use_mock_cache: bool | None = None


def _use_mock() -> bool:
    global _use_mock_cache
    if _use_mock_cache is None:
        _use_mock_cache = os.getenv("USE_MOCK_AZURE", "true").lower() == "true"
    return _use_mock_cache


# ── Abbreviation expansion (D-05) ─────────────────────────────────────────────

ABBREV_MAP: dict[str, str] = {
    "HbA1c": "hemoglobina glicada",
    "PA": "pressão arterial",
    "FC": "frequência cardíaca",
    "FR": "frequência respiratória",
    "SpO2": "saturação de oxigênio",
}


def expand_abbreviations(text: str) -> str:
    """Expand Portuguese medical abbreviations before LLM interpreter call (D-05)."""
    for abbrev, expansion in ABBREV_MAP.items():
        text = re.sub(rf'\b{re.escape(abbrev)}\b', expansion, text)
    return text


# ── RoutingResult model (D-02, Pitfall 5 fix: list[str] NOT tuple) ────────────

class RoutingResult(BaseModel):
    intent: Literal["sql_only", "search_only", "mixed"]
    entities: list[str] = []
    time_range: list[str] | None = None   # [ISO start, ISO end] e.g. ["2024-01-01", "2024-12-31"]
    sql_steps: list[str] = []             # e.g. ["observations:hemoglobina glicada", "medications:active"]
    search_queries: list[str] = []        # expanded query strings for search()


# ── Router system prompt (template — rendered per call with patient summary) ──

_ROUTER_SYSTEM_PROMPT_TEMPLATE = """You are a clinical query router for a Brazilian medical records system. Today is {today}.

The patient's current profile is shown below. Use the EXACT analyte names, medication names, and condition names from this profile when generating sql_steps — do not invent or normalize names.

{patient_summary_block}

Analyze the user query and return a JSON object with EXACTLY these fields:
- "intent": one of "sql_only", "search_only", "mixed"
  - sql_only: questions about specific values, trends, or lists already present in the patient profile (labs, medications, conditions, allergies, imaging)
  - search_only: narrative questions about what a doctor said, visit notes, clinical opinions, or topics NOT present in the profile
  - mixed: questions requiring both structured data AND narrative documents
- "entities": list of clinical entities extracted from the query (use expanded Portuguese forms)
- "time_range": null OR [ISO_start_date, ISO_end_date] if a time period is mentioned
- "sql_steps": list of step keys for sql_only or mixed intent. Valid step keys:
  - "observations:{{analyte}}" — use the EXACT analyte name from the patient profile
  - "observations:{{analyte}}:range:{{start}}:{{end}}" — lab values in ISO date range
  - "medications:active" — active medications
  - "conditions:active" — active conditions
  - "allergies:all" — all allergies
  - "imaging:recent" — recent imaging findings
- "search_queries": list of search query strings for search_only or mixed intent

Return ONLY the JSON object, no explanation. For sql_only, search_queries may be empty. For search_only, sql_steps must be empty."""


# ── Patient summary builder ───────────────────────────────────────────────────

def build_patient_summary(user_id: str) -> str:
    """
    Build a compact clinical profile for a patient from all structured tables.

    Used as:
    1. Anchor context in the router prompt (so router uses exact analyte names)
    2. Always-present section in the final context sent to the LLM

    Soft-fail per table: one table failing doesn't break the whole summary.
    Returns empty string when no structured data exists.
    """
    client = _get_client()
    sections: list[str] = []

    # Active conditions
    try:
        resp = (
            client.table("patient_conditions")
            .select("raw_condition,clinical_status")
            .eq("user_id", user_id)
            .eq("clinical_status", "active")
            .limit(10)
            .execute()
        )
        if resp.data:
            items = [r["raw_condition"] for r in resp.data if r.get("raw_condition")]
            if items:
                sections.append("Condições ativas: " + ", ".join(items))
    except Exception as e:
        logger.warning("build_patient_summary: conditions failed: %s", e)

    # Active medications
    try:
        resp = (
            client.table("patient_medications")
            .select("raw_medication,dose,frequency")
            .eq("user_id", user_id)
            .eq("status", "active")
            .limit(10)
            .execute()
        )
        if resp.data:
            items = []
            for r in resp.data:
                med = r.get("raw_medication", "")
                dose = r.get("dose") or ""
                freq = r.get("frequency") or ""
                items.append(f"{med} {dose} {freq}".strip())
            if items:
                sections.append("Medicamentos ativos: " + ", ".join(items))
    except Exception as e:
        logger.warning("build_patient_summary: medications failed: %s", e)

    # All allergies
    try:
        resp = (
            client.table("patient_allergies")
            .select("raw_allergen,reaction")
            .eq("user_id", user_id)
            .limit(10)
            .execute()
        )
        if resp.data:
            items = []
            for r in resp.data:
                allergen = r.get("raw_allergen", "")
                reaction = r.get("reaction") or ""
                items.append(f"{allergen} ({reaction})" if reaction else allergen)
            if items:
                sections.append("Alergias: " + ", ".join(items))
    except Exception as e:
        logger.warning("build_patient_summary: allergies failed: %s", e)

    # Recent lab observations (last 20, most recent first)
    try:
        resp = (
            client.table("patient_observations")
            .select("normalized_analyte,value_str,unit,flag,observed_date")
            .eq("user_id", user_id)
            .order("observed_date", desc=True)
            .limit(20)
            .execute()
        )
        if resp.data:
            obs_lines: list[str] = []
            for r in resp.data:
                analyte = r.get("normalized_analyte", "")
                value = r.get("value_str", "")
                unit = r.get("unit") or ""
                flag = r.get("flag") or ""
                obs_date = (r.get("observed_date") or "")[:10]
                flag_str = f" [{flag}]" if flag else ""
                unit_str = f" {unit}" if unit else ""
                date_str = f" ({obs_date})" if obs_date else ""
                obs_lines.append(f"  {analyte}: {value}{unit_str}{flag_str}{date_str}")
            if obs_lines:
                sections.append("Exames laboratoriais:\n" + "\n".join(obs_lines))
    except Exception as e:
        logger.warning("build_patient_summary: observations failed: %s", e)

    # Recent imaging findings
    try:
        resp = (
            client.table("patient_imaging_findings")
            .select("modality,body_region,impression")
            .eq("user_id", user_id)
            .order("id", desc=True)
            .limit(3)
            .execute()
        )
        if resp.data:
            items = []
            for r in resp.data:
                modality = r.get("modality") or ""
                region = r.get("body_region") or ""
                impression = (r.get("impression") or "")[:120]
                items.append(f"{modality} {region}: {impression}".strip())
            if items:
                sections.append("Exames de imagem: " + "; ".join(items))
    except Exception as e:
        logger.warning("build_patient_summary: imaging failed: %s", e)

    if not sections:
        return ""

    return "=== PERFIL CLÍNICO DO PACIENTE ===\n" + "\n".join(sections) + "\n=== FIM DO PERFIL ==="


# ── route_query (D-01, D-03, D-04, mock guard per Pitfall 2) ─────────────────

def route_query(question: str, user_id: str, patient_summary: str = "") -> RoutingResult:
    """
    LLM-based query interpreter: classifies intent, extracts entities, resolves temporal references.

    Args:
        question: Raw user question (Portuguese).
        user_id: Authenticated user ID — used for SQL scoping (not passed to LLM).
        patient_summary: Pre-built compact patient profile from build_patient_summary().
                         Injected into router prompt so the LLM uses exact analyte/med names.

    Returns:
        RoutingResult with intent, entities, time_range, sql_steps, search_queries.
        On any failure, falls back to search_only (D-04).
    """
    # Mock guard — return search_only without LLM call (Pitfall 2: mock returns "{}" which would fail RoutingResult validation)
    if _use_mock():
        expanded = expand_abbreviations(question)
        return RoutingResult(intent="search_only", search_queries=[expanded])

    expanded = expand_abbreviations(question)

    summary_block = patient_summary if patient_summary else "(Nenhum dado estruturado disponível para este paciente.)"
    prompt = _ROUTER_SYSTEM_PROMPT_TEMPLATE.format(
        today=date.today().isoformat(),
        patient_summary_block=summary_block,
    )

    try:
        raw = generate_json(prompt, expanded)
        data = json.loads(raw)
        result = RoutingResult(**data)
        logger.debug("route_query intent=%s entities=%s steps=%s", result.intent, result.entities, result.sql_steps)
        return result
    except Exception as e:
        logger.warning("route_query failed, fallback to search_only: %s", e)
        return RoutingResult(intent="search_only", search_queries=[expanded])


# ── SQL executor functions ────────────────────────────────────────────────────

def execute_sql_steps(sql_steps: list[str], user_id: str) -> list[dict]:
    """
    Execute each sql_step string against patient tables via Supabase SDK.

    user_id is ALWAYS injected by this function — never by the LLM.
    Returns list of result dicts, one per step. Empty list on total failure.

    Step key format:
      "observations:{analyte}" — latest 10 obs for analyte
      "observations:{analyte}:range:{start}:{end}" — obs in ISO date range
      "medications:active" — active medications
      "conditions:active" — active conditions
      "allergies:all" — all allergies
      "imaging:recent" — 5 most recent imaging findings
    """
    results: list[dict] = []
    for step in sql_steps:
        try:
            row = _execute_single_step(step, user_id)
            if row:
                results.append(row)
        except Exception as e:
            logger.warning("SQL step '%s' failed (soft-fail, D-09): %s", step, e)
    return results


def _execute_single_step(step: str, user_id: str) -> dict | None:
    """Dispatch a single sql_step key to the correct Supabase query template."""
    client = _get_client()

    # observations:{analyte} or observations:{analyte}:range:{start}:{end}
    if step.startswith("observations:"):
        parts = step.split(":")
        analyte = parts[1]
        if len(parts) == 5 and parts[2] == "range":
            start_date, end_date = parts[3], parts[4]
            resp = (
                client.table("patient_observations")
                .select("normalized_analyte,value_str,unit,flag,observed_date")
                .eq("user_id", user_id)
                .eq("normalized_analyte", analyte)
                .gte("observed_date", start_date)
                .lte("observed_date", end_date)
                .order("observed_date", desc=True)
                .limit(10)
                .execute()
            )
        else:
            resp = (
                client.table("patient_observations")
                .select("normalized_analyte,value_str,unit,flag,observed_date")
                .eq("user_id", user_id)
                .eq("normalized_analyte", analyte)
                .order("observed_date", desc=True)
                .limit(10)
                .execute()
            )
        return {"step": step, "table": "patient_observations", "rows": resp.data or []}

    elif step == "medications:active":
        resp = (
            client.table("patient_medications")
            .select("raw_medication,dose,frequency,route")
            .eq("user_id", user_id)
            .eq("status", "active")
            .limit(20)
            .execute()
        )
        return {"step": step, "table": "patient_medications", "rows": resp.data or []}

    elif step == "conditions:active":
        resp = (
            client.table("patient_conditions")
            .select("raw_condition,clinical_status,verification_status")
            .eq("user_id", user_id)
            .eq("clinical_status", "active")
            .limit(20)
            .execute()
        )
        return {"step": step, "table": "patient_conditions", "rows": resp.data or []}

    elif step == "allergies:all":
        resp = (
            client.table("patient_allergies")
            .select("raw_allergen,reaction")
            .eq("user_id", user_id)
            .limit(20)
            .execute()
        )
        return {"step": step, "table": "patient_allergies", "rows": resp.data or []}

    elif step == "imaging:recent":
        resp = (
            client.table("patient_imaging_findings")
            .select("modality,body_region,impression,urgency")
            .eq("user_id", user_id)
            .order("id", desc=True)
            .limit(5)
            .execute()
        )
        return {"step": step, "table": "patient_imaging_findings", "rows": resp.data or []}

    else:
        logger.warning("Unknown sql_step key '%s' — skipping", step)
        return None


def format_sql_block(sql_results: list[dict]) -> str:
    """
    Format SQL result rows as a compact plain-text block for Claude's prompt (D-12).

    Budget: cap at ~3200 characters (~800 tokens). Returns empty string if no data.
    """
    if not sql_results:
        return ""

    lines: list[str] = ["=== DADOS ESTRUTURADOS DO PACIENTE ==="]
    char_count = len(lines[0])

    for result in sql_results:
        table = result.get("table", "")
        rows = result.get("rows", [])
        if not rows:
            continue

        if table == "patient_observations":
            # Group rows by analyte and list chronologically
            for row in rows:
                analyte = row.get("normalized_analyte", "")
                value = row.get("value_str", "")
                unit = row.get("unit", "")
                flag = row.get("flag", "")
                obs_date = row.get("observed_date", "")
                flag_str = f" [{flag}]" if flag else ""
                unit_str = f" {unit}" if unit else ""
                line = f"{analyte}: {value}{unit_str}{flag_str} ({obs_date})"
                if char_count + len(line) > 3200:
                    break
                lines.append(line)
                char_count += len(line)

        elif table == "patient_medications":
            for row in rows:
                name = row.get("raw_medication", "")
                dose = row.get("dose", "")
                freq = row.get("frequency", "")
                dose_str = f" {dose}" if dose else ""
                freq_str = f" — {freq}" if freq else ""
                line = f"Medicamento: {name}{dose_str}{freq_str}"
                if char_count + len(line) > 3200:
                    break
                lines.append(line)
                char_count += len(line)

        elif table == "patient_conditions":
            for row in rows:
                condition = row.get("raw_condition", "")
                status = row.get("clinical_status", "")
                line = f"Condição: {condition} ({status})"
                if char_count + len(line) > 3200:
                    break
                lines.append(line)
                char_count += len(line)

        elif table == "patient_allergies":
            for row in rows:
                allergen = row.get("raw_allergen", "")
                reaction = row.get("reaction", "")
                reaction_str = f" — reação: {reaction}" if reaction else ""
                line = f"Alergia: {allergen}{reaction_str}"
                if char_count + len(line) > 3200:
                    break
                lines.append(line)
                char_count += len(line)

        elif table == "patient_imaging_findings":
            for row in rows:
                modality = row.get("modality", "")
                region = row.get("body_region", "")
                impression = row.get("impression", "")
                urgency = row.get("urgency", "")
                urgency_str = f" [urgência: {urgency}]" if urgency else ""
                line = f"Imagem ({modality} — {region}): {impression}{urgency_str}"
                if char_count + len(line) > 3200:
                    break
                lines.append(line)
                char_count += len(line)

    lines.append("=== FIM DOS DADOS ESTRUTURADOS ===")

    if len(lines) <= 2:  # only header and footer — no actual data
        return ""
    return "\n".join(lines)


# ── Chat context assembler (RETRIEVE-05 / D-11) ───────────────────────────────


def _fetch_structured_result(doc_id: str) -> StructuredResult | None:
    """Fetch structured_result from documents table by doc_id. Soft-fail: returns None on any error."""
    try:
        client = _get_client()
        resp = client.table("documents").select("structured_result").eq("id", doc_id).single().execute()
        if resp.data is None or not resp.data.get("structured_result"):
            return None
        sr_data = resp.data["structured_result"]
        return StructuredResult(**sr_data)
    except Exception as e:
        logger.warning("_fetch_structured_result failed for doc_id=%s: %s", doc_id, e)
        return None


def assemble_chat_block(
    doc_id: str,
    source_name: str,
    excerpt: str,
    collection_date: str | None = None,
) -> str:
    """Assemble a compact clinical block for Claude prompt. Max ~1200 chars (~300 tokens).
    Soft-fail: falls back to raw excerpt when structured_result unavailable."""
    sr = _fetch_structured_result(doc_id)
    family = sr.document_family if sr else "unknown"
    date_str = collection_date or "data desconhecida"
    header = f"[Fonte: {source_name} | {family} | {date_str}]"

    if sr is None:
        return f"{header}\n{excerpt[:400]}"

    parts = [header]

    try:
        if sr.document_family == "structured_lab":
            lab = StructuredLab(**sr.structured_data)
            if lab.summary:
                parts.append(f"Summary: {lab.summary[:200]}")
            if lab.findings:
                finding_strs = []
                for f in lab.findings[:10]:
                    s = f"{f.name}: {f.value}"
                    if f.unit:
                        s += f" {f.unit}"
                    if f.flag:
                        s += f" [{f.flag}]"
                    finding_strs.append(s)
                parts.append(f"Findings: {' | '.join(finding_strs)}")
            entities = lab.entities_for_memory or sr.entities_for_memory
            if entities:
                parts.append(f"Entities: {', '.join(e for e in entities if e)[:150]}")

        elif sr.document_family == "imaging_narrative":
            report = ImagingReport(**sr.structured_data)
            if report.summary:
                parts.append(f"Summary: {report.summary[:200]}")
            text = report.impression or report.findings
            if text:
                parts.append(f"Findings: {text[:300]}")
            entities = report.entities_for_memory or sr.entities_for_memory
            if entities:
                parts.append(f"Entities: {', '.join(e for e in entities if e)[:150]}")

        elif sr.document_family == "clinical_narrative":
            note = ClinicalNote(**sr.structured_data)
            if note.summary:
                parts.append(f"Summary: {note.summary[:200]}")
            if note.diagnoses:
                parts.append(f"Findings: {', '.join(d for d in note.diagnoses if d)[:300]}")
            entities = note.entities_for_memory or sr.entities_for_memory
            if entities:
                parts.append(f"Entities: {', '.join(e for e in entities if e)[:150]}")

        elif sr.document_family == "medication_document":
            med_doc = MedicationDocument(**sr.structured_data)
            if med_doc.summary:
                parts.append(f"Summary: {med_doc.summary[:200]}")
            if med_doc.medications:
                med_strs = [
                    m.name + (f" {m.dose}" if m.dose else "") + (f" - {m.frequency}" if m.frequency else "")
                    for m in med_doc.medications[:10]
                ]
                parts.append(f"Findings: {' | '.join(med_strs)}")
            entities = med_doc.entities_for_memory or sr.entities_for_memory
            if entities:
                parts.append(f"Entities: {', '.join(e for e in entities if e)[:150]}")

        else:
            # Unknown family — fall back to excerpt
            parts.append(excerpt[:400])

    except Exception as e:
        logger.warning("assemble_chat_block dispatch failed for doc_id=%s family=%s: %s", doc_id, sr.document_family, e)
        parts.append(excerpt[:400])

    block = "\n".join(parts)
    return block[:1200]
