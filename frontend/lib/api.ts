const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Erro ao fazer upload");
  }

  return res.json();
}

export async function listDocuments(): Promise<{
  documents: Array<{
    id: string;
    original_name: string;
    upload_date: string;
    entity_count: number;
  }>;
  total: number;
}> {
  const res = await fetch(`${API_BASE}/documents`);
  if (!res.ok) throw new Error("Erro ao listar documentos");
  return res.json();
}

export interface Entity {
  text: string;
  category: string;
  normalized_text: string | null;
  confidence: number;
}

export interface DocumentDetail {
  document_id: string;
  original_name: string;
  upload_date: string;
  anonymized_text: string;
  medical_entities: Entity[];
  pii_substitutions: string[];
}

export async function getDocument(docId: string): Promise<DocumentDetail> {
  const res = await fetch(`${API_BASE}/documents/${docId}`);
  if (!res.ok) throw new Error("Documento não encontrado");
  return res.json();
}
