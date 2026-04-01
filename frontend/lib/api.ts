import { getAccessToken } from "./supabase";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

async function authHeaders(): Promise<HeadersInit> {
  const token = await getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function parseError(res: Response): Promise<string> {
  try {
    const err = await res.json();
    return err.detail || `Erro ${res.status}`;
  } catch {
    return `Erro ${res.status}`;
  }
}

export async function uploadDocument(file: File): Promise<{
  document_id: string;
  message: string;
  entity_count: number;
  blob_url: string;
}> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    headers: await authHeaders(),
    body: formData,
  });

  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function listDocuments(): Promise<{
  documents: Array<{
    id: string;
    original_name: string;
    upload_date: string;
    entity_count: number;
    document_family: string | null;
    summary: string | null;
  }>;
  total: number;
}> {
  const res = await fetch(`${API_BASE}/documents`, { headers: await authHeaders() });
  if (!res.ok) throw new Error("Erro ao listar documentos");
  return res.json();
}

export function documentFileUrl(docId: string): string {
  return `${API_BASE}/documents/${docId}/file`;
}

export interface Entity {
  text: string;
  category: string;
  normalized_text: string | null;
  confidence: number;
}

export interface LabFinding {
  name: string;
  value: string;
  unit: string | null;
  reference_range: string | null;
  flag: "normal" | "high" | "low" | "borderline" | "critical" | null;
  is_clinically_actionable: boolean;
}

export interface StructuredLab {
  document_family: "structured_lab";
  exam_name: string | null;
  collection_date: string | null;
  release_date: string | null;
  sample_type: string | null;
  findings: LabFinding[];
  summary: string | null;
  entities_for_memory: string[];
}

export interface ImagingReport {
  document_family: "imaging_narrative";
  modality: string | null;
  body_region: string | null;
  indication: string | null;
  findings: string | null;
  impression: string | null;
  recommendations: string | null;
  urgency: "routine" | "urgent" | "critical" | null;
  comparison_with_prior: string | null;
  summary: string | null;
  entities_for_memory: string[];
}

export interface ClinicalNote {
  document_family: "clinical_narrative";
  chief_complaint: string | null;
  symptoms: string[];
  diagnoses: string[];
  suspected_diagnoses: string[];
  allergies: string[];
  medications: string[];
  conduct: string | null;
  follow_up: string | null;
  specialties: string[];
  summary: string | null;
  entities_for_memory: string[];
}

export interface MedicationDocument {
  document_family: "medication_document";
  medications: Array<{
    name: string;
    dose: string | null;
    route: string | null;
    frequency: string | null;
    duration: string | null;
    indication: string | null;
  }>;
  summary: string | null;
  entities_for_memory: string[];
}

export type StructuredData = StructuredLab | ImagingReport | ClinicalNote | MedicationDocument | Record<string, unknown>;

export interface StructuredResult {
  document_family: string;
  document_subtype: string | null;
  extraction_confidence: number;
  processing_version: string;
  admin_metadata: Record<string, unknown>;
  structured_data: StructuredData;
  entities_for_memory: string[];
  raw_clinical_text: string | null;
}

export interface DocumentDetail {
  document_id: string;
  original_name: string;
  upload_date: string;
  anonymized_text: string;
  medical_entities: Entity[];
  pii_substitutions: string[];
  structured_result: StructuredResult | null;
  file_blob_url: string | null;
}

export type HealthEntryType = "medication_current" | "medication_past" | "complaint" | "allergy";

export interface HealthEntry {
  id: string;
  user_id: string;
  entry_type: HealthEntryType;
  name: string;
  details: string | null;
  started_at: string | null;
  ended_at: string | null;
  active: boolean;
  created_at: string;
}

export interface HealthEntryCreate {
  entry_type: HealthEntryType;
  name: string;
  details?: string;
  started_at?: string;
  ended_at?: string;
}

export async function listHealthEntries(): Promise<HealthEntry[]> {
  const res = await fetch(`${API_BASE}/saude`, { headers: await authHeaders() });
  if (!res.ok) throw new Error("Erro ao carregar entradas de saúde");
  return res.json();
}

export async function createHealthEntry(entry: HealthEntryCreate): Promise<HealthEntry> {
  const res = await fetch(`${API_BASE}/saude`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...await authHeaders() },
    body: JSON.stringify(entry),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function deleteHealthEntry(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/saude/${id}`, {
    method: "DELETE",
    headers: await authHeaders(),
  });
  if (!res.ok) throw new Error(await parseError(res));
}

export async function getDocument(docId: string): Promise<DocumentDetail> {
  const res = await fetch(`${API_BASE}/documents/${docId}`, { headers: await authHeaders() });
  if (!res.ok) throw new Error("Documento não encontrado");
  return res.json();
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: string[];
}

export interface ChatStreamCallbacks {
  onSources: (sources: string[]) => void;
  onToken: (token: string) => void;
  onDone: () => void;
  onError: (err: string) => void;
}

export async function chatStream(
  message: string,
  history: ChatMessage[],
  callbacks: ChatStreamCallbacks,
): Promise<void> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...await authHeaders() },
    body: JSON.stringify({ message, history }),
  });

  if (!res.ok || !res.body) {
    callbacks.onError("Erro ao conectar com o agente IA");
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const lines = decoder.decode(value).split("\n");
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      try {
        const event = JSON.parse(line.slice(6));
        if (event.type === "sources") callbacks.onSources(event.sources);
        else if (event.type === "token") callbacks.onToken(event.content);
        else if (event.type === "done") callbacks.onDone();
      } catch {
        // linha incompleta, ignora
      }
    }
  }
}

export interface SuggestedSpecialty {
  specialty: string;
  reason: string;
}

export interface AnalysisResult {
  user_id: string;
  case_summary: string;
  diagnoses: string[];
  active_medications: string[];
  allergies: string[];
  suggested_specialties: SuggestedSpecialty[];
  document_count: number;
  disclaimer: string;
}

export async function getAnalysis(): Promise<AnalysisResult> {
  const res = await fetch(`${API_BASE}/analysis`, { headers: await authHeaders() });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Erro ao carregar análise");
  }
  return res.json();
}

export interface EmergencyAllergy {
  name: string;
  severity: string;
}

export interface EmergencyMedication {
  name: string;
  dose: string;
  alert: string | null;
}

export interface EmergencyProfile {
  user_id: string;
  blood_type: string | null;
  allergies: EmergencyAllergy[];
  active_medications: EmergencyMedication[];
  active_conditions: string[];
  last_updated: string;
}

export async function getEmergencyProfile(userId: string): Promise<EmergencyProfile> {
  const res = await fetch(`${API_BASE}/emergency/${userId}`);
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Perfil de emergência não encontrado");
  }
  return res.json();
}

export function emergencyPdfUrl(userId: string): string {
  return `${API_BASE}/emergency/${userId}/pdf`;
}

export function emergencyQrUrl(userId: string): string {
  return `${API_BASE}/emergency/${userId}/qr`;
}
