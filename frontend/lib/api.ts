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
    headers: { "Content-Type": "application/json" },
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
