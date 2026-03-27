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
