"use client";

import { useEffect, useState } from "react";
import { FileText, Clock, ChevronRight, FlaskConical, Scan, ClipboardList, Pill } from "lucide-react";
import { listDocuments } from "@/lib/api";
import { DocumentDetail } from "./DocumentDetail";

interface Doc {
  id: string;
  original_name: string;
  upload_date: string;
  entity_count: number;
  document_family: string | null;
  summary: string | null;
}

const FAMILY_META: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  structured_lab:      { label: "Exame laboratorial", icon: FlaskConical, color: "bg-purple-50 text-purple-700" },
  imaging_narrative:   { label: "Laudo de imagem",    icon: Scan,         color: "bg-indigo-50 text-indigo-700" },
  clinical_narrative:  { label: "Nota clínica",       icon: ClipboardList, color: "bg-blue-50 text-blue-700" },
  medication_document: { label: "Prescrição",          icon: Pill,         color: "bg-green-50 text-green-700" },
};

function FamilyBadge({ family }: { family: string | null }) {
  const meta = family ? FAMILY_META[family] : null;
  const label = meta?.label ?? "Documento médico";
  const color = meta?.color ?? "bg-gray-100 text-gray-500";
  const Icon = meta?.icon ?? FileText;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${color}`}>
      <Icon className="h-3 w-3" />
      {label}
    </span>
  );
}

export function DocumentList({ refreshKey }: { refreshKey?: number }) {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    listDocuments()
      .then((data) => setDocs(data.documents))
      .finally(() => setLoading(false));
  }, [refreshKey]);

  if (loading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 animate-pulse rounded-lg bg-gray-100" />
        ))}
      </div>
    );
  }

  if (docs.length === 0) {
    return (
      <p className="text-center text-sm text-gray-500 py-8">
        Nenhum documento enviado ainda.
      </p>
    );
  }

  return (
    <>
      <ul className="space-y-2">
        {docs.map((doc) => (
          <li key={doc.id}>
            <button
              onClick={() => setSelectedId(doc.id)}
              className="w-full flex items-center gap-3 rounded-lg border border-gray-200 bg-white p-4 hover:border-blue-300 hover:shadow-sm transition-all text-left"
            >
              <FileText className="h-5 w-5 shrink-0 text-blue-500" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-800 truncate">{doc.original_name}</p>
                <div className="flex items-center gap-2 mt-1 flex-wrap">
                  <FamilyBadge family={doc.document_family} />
                  <span className="flex items-center gap-1 text-xs text-gray-400">
                    <Clock className="h-3 w-3" />
                    {new Date(doc.upload_date).toLocaleDateString("pt-BR")}
                  </span>
                </div>
                {doc.summary && (
                  <p className="mt-1 text-xs text-gray-500 truncate max-w-lg">{doc.summary}</p>
                )}
              </div>
              <ChevronRight className="h-4 w-4 text-gray-400 shrink-0" />
            </button>
          </li>
        ))}
      </ul>

      {selectedId && (
        <DocumentDetail docId={selectedId} onClose={() => setSelectedId(null)} />
      )}
    </>
  );
}
