# Research: Clinical Reasoning and LLM Patterns

## Clinical Summarization

**Core principle:** Never pass raw document text to the LLM for summarization. Always aggregate structured data first.

**Patient block structure** (given UHR's existing extraction schema):
```python
patient_block = {
    "demographics": {},          # from health_profile
    "active_conditions": [],     # from patient_conditions WHERE clinical_status='active'
    "active_medications": [],    # from patient_medications WHERE status='active'
    "allergies": [],             # from patient_allergies
    "recent_labs": [],           # patient_observations last 12 months, grouped by analyte
    "recent_imaging": [],        # patient_imaging_findings last 24 months
    "recent_visits": [],         # clinical_narrative documents last 12 months, impression only
}
```

**Temporal windowing:** Always constrain the summary window explicitly (e.g., "last 12 months" for active issues, "all time" for conditions/allergies). Unbounded summaries become unwieldy for long-term patients.

**What NOT to include:** Raw OCR text, full document bodies, redundant entries from the same date. Summarize at the entity level, not the document level.

## Differential Diagnosis Generation

**Three-tier framework (standard clinical reasoning):**
1. **Most likely** — highest probability given age, history, presentation
2. **Must not miss** — serious/emergent conditions that warrant exclusion even if less probable
3. **Possible** — consistent with findings but lower probability

**Why "diagnose" fails:** Prompting Claude to "provide a diagnosis" produces confident single answers. Prompting for "conditions consistent with these findings" produces calibrated differentials with evidence and uncertainty. Use the latter.

**Forced chain-of-thought pattern:**
```
Step 1: List the key findings from the patient data
Step 2: For each finding, list conditions that commonly produce it
Step 3: Identify which conditions explain the most findings simultaneously
Step 4: Classify each candidate into (most likely / must not miss / possible)
Step 5: For each candidate, cite the specific findings that support it
Step 6: Note what additional information would change the ranking
```

**Evidence anchoring:** Each differential entry must cite specific patient data points (lab values, dates, document references) — not general medical knowledge. This is what separates a useful copilot response from a generic textbook answer.

## Safety Guardrails

**Structural guardrails (enforce in code, not just prompts):**
- Citation requirement: LLM output must reference specific source documents/values; reject responses without citations
- Scope boundary: output schema includes an `is_outside_scope` flag; any response claiming to diagnose definitively triggers a soft rejection
- Grounding enforcement: at output validation time, verify that cited values actually exist in the patient data passed in

**The disclaimer problem:**
- Boilerplate disclaimers ("I am not a doctor...") are ignored by users and add noise
- What works: **contextual + actionable hedges** embedded in the response itself
  - Bad: "This is not medical advice. Consult a doctor."
  - Good: "HbA1c of 7.8% (Aug 2024) suggests suboptimal glycemic control — your endocrinologist should confirm whether medication adjustment is warranted."

**Claude sycophancy risk:** Claude tends to agree with user framings in medical context. Counter-pattern: include a required `contradicting_evidence` field in the structured output schema that forces the model to surface findings that argue against each differential.

## Structured Output Schema

Extend existing `AnalysisResult` to a `ClinicalReasoningResult`:

```python
class EvidenceReference(BaseModel):
    source_document_id: str | None
    data_type: str  # "lab", "condition", "medication", "imaging", "manual"
    description: str
    value: str | None
    date: str | None

class DifferentialEntry(BaseModel):
    condition: str
    tier: Literal["most_likely", "must_not_miss", "possible"]
    supporting_evidence: list[EvidenceReference]
    contradicting_evidence: list[EvidenceReference]
    confidence: Literal["low", "moderate", "high"]
    confidence_rationale: str
    suggested_next_step: str | None

class RelevantFinding(BaseModel):
    finding: str
    significance: str
    source: EvidenceReference

class ClinicalReasoningResult(BaseModel):
    case_summary: str
    key_findings: list[RelevantFinding]
    differentials: list[DifferentialEntry]
    suggested_specialties: list[str]
    information_gaps: list[str]  # what additional data would improve reasoning
    reasoning_scope: str  # what patient data window was used
    is_outside_scope: bool  # true if question can't be answered from available data
```

## Claude-Specific Behavior

**Strengths for this use case:**
- Strong instruction following — structured output schemas are respected
- Hedging calibration — naturally expresses uncertainty without over-prompting
- JSON adherence — reliable for Pydantic-compatible structured outputs

**Known limitations:**
- **Sycophancy** — agrees with user clinical framings; must be counteracted structurally
- **Training cutoff** — clinical guidelines from after August 2025 not reflected
- **Entity drift in long contexts** — in very long patient histories, early-mentioned entities can be misattributed; keep patient block under ~8K tokens
- **OCR text degradation** — corrupted text from OCR produces hallucinated "corrections"; this is why fixing ingestion is Milestone 1

**Extended thinking:** Beneficial for differential generation (forces multi-step reasoning). However, Azure OpenAI endpoint does NOT support extended thinking — requires direct Anthropic API (`anthropic` SDK). Verify which endpoint is used in `services/azure/llm.py` before Milestone 3 planning.

## Two-Call Architecture

Separate calls for case summary and differential generation. Do not combine.

| Call | Purpose | Output format | Streaming? |
|------|---------|---------------|------------|
| Call 1: Summary | Condense patient data into structured case summary | `ClinicalReasoningResult` (partial) | No — structured JSON |
| Call 2: Differentials | Generate differentials from summary + full patient block | `ClinicalReasoningResult` (complete) | No — structured JSON |
| Chat | Answer freeform clinical questions | Markdown text | Yes — SSE |

The two-call separation allows caching the case summary (recompute only when new documents arrive) while differentials are generated on demand.

## Evaluation Without Ground Truth

**Automatable checks:**
1. **Citation accuracy** — verify that cited document IDs exist and cited values match stored data
2. **Schema conformance** — validate Pydantic model; non-conforming outputs are caught at the boundary
3. **Internal consistency** — contradicting evidence should not overlap with supporting evidence for the same differential
4. **Self-evaluation prompting** — as a final step, prompt Claude with the output and ask "what in this response is unsupported by the provided patient data?" — flag responses with non-empty answers for review

## Key Gaps to Resolve Before Milestone 3

1. **Azure vs Anthropic endpoint** — confirm whether `services/azure/llm.py` calls Azure OpenAI or direct Anthropic API; extended thinking requires direct Anthropic API
2. **Vector search tier** — verify Azure AI Search tier supports vector fields (Basic tier does not)
3. **Context window strategy** — for patients with 50+ documents, patient block must be summarized before injection; design a summarization cache
4. **Portuguese prompt tuning** — clinical reasoning prompts may need Portuguese variants for medical terminology accuracy; test both
