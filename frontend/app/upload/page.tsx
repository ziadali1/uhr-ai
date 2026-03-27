"use client";

import { useState } from "react";
import { UploadZone } from "@/components/upload/UploadZone";
import { DocumentList } from "@/components/upload/DocumentList";

export default function UploadPage() {
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Documentos Médicos</h1>
        <p className="mt-1 text-sm text-gray-500">
          PDFs e imagens são processados por OCR e anonimizados automaticamente antes de serem armazenados.
        </p>
      </div>

      <UploadZone onSuccess={() => setRefreshKey((k) => k + 1)} />

      <div>
        <h2 className="mb-4 text-base font-semibold text-gray-800">Documentos enviados</h2>
        <DocumentList refreshKey={refreshKey} />
      </div>
    </div>
  );
}
