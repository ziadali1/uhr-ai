"use client";

import { useEffect, useState } from "react";
import { FileText, Clock, Tag, ChevronRight } from "lucide-react";
import { listDocuments } from "@/lib/api";
import { DocumentDetail } from "./DocumentDetail";

interface Doc {
  id: string;
  original_name: string;
  upload_date: string;
  entity_count: number;
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
                <div className="flex items-center gap-3 mt-0.5">
                  <span className="flex items-center gap-1 text-xs text-gray-500">
                    <Clock className="h-3 w-3" />
                    {new Date(doc.upload_date).toLocaleDateString("pt-BR")}
                  </span>
                  <span className="flex items-center gap-1 text-xs text-gray-500">
                    <Tag className="h-3 w-3" />
                    {doc.entity_count} entidades
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-xs text-green-600 font-medium bg-green-50 px-2 py-0.5 rounded-full">
                  Anonimizado
                </span>
                <ChevronRight className="h-4 w-4 text-gray-400" />
              </div>
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
