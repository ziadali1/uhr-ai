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


# ── Router system prompt ──────────────────────────────────────────────────────

_ROUTER_SYSTEM_PROMPT = f"""You are a clinical query router for a Brazilian medical records system. Today is {date.today().isoformat()}.

Analyze the user query and return a JSON object with EXACTLY these fields:
- "intent": one of "sql_only", "search_only", "mixed"
  - sql_only: numeric/aggregation questions about specific lab values, active medications, active conditions, allergies, or imaging findings
  - search_only: narrative questions about what a doctor said, visit notes, clinical opinions, explanations
  - mixed: questions requiring both structured data AND narrative documents
- "entities": list of clinical entities extracted (analyte names, medications, conditions) — use expanded Portuguese forms
- "time_range": null OR [ISO_start_date, ISO_end_date] if a time period is mentioned
- "sql_steps": list of step keys for sql_only or mixed intent. Valid step keys:
  - "observations:{{analyte_name}}" — retrieve lab values for a specific analyte
  - "observations:{{analyte_name}}:range:{{start}}:{{end}}" — lab values in date range (ISO dates)
  - "medications:active" — active medications
  - "conditions:active" — active conditions
  - "allergies:all" — all allergies
  - "imaging:recent" — recent imaging findings
- "search_queries": list of search query strings for search_only or mixed intent

Return ONLY the JSON object, no explanation. For sql_only, search_queries may be empty. For search_only, sql_steps must be empty."""


# ── route_query (D-01, D-03, D-04, mock guard per Pitfall 2) ─────────────────

def route_query(question: str, user_id: str) -> RoutingResult:
    """
    LLM-based query interpreter: classifies intent, extracts entities, resolves temporal references.

    Args:
        question: Raw user question (Portuguese).
        user_id: Authenticated user ID — used for SQL scoping (not passed to LLM).

    Returns:
        RoutingResult with intent, entities, time_range, sql_steps, search_queries.
        On any failure, falls back to search_only (D-04).
    """
    # Mock guard — return search_only without LLM call (Pitfall 2: mock returns "{}" which would fail RoutingResult validation)
    if _use_mock():
        expanded = expand_abbreviations(question)
        return RoutingResult(intent="search_only", search_queries=[expanded])

    expanded = expand_abbreviations(question)

    try:
        raw = generate_json(_ROUTER_SYSTEM_PROMPT, expanded)
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
