"use client";

import { useEffect, useState } from "react";
import { getDocument, type DocumentDetail } from "@/lib/api";
import { Loader2, Pill, Stethoscope, AlertTriangle, X } from "lucide-react";

const CATEGORY_LABELS: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  Diagnosis: { label: "Diagnóstico", icon: Stethoscope, color: "text-blue-700 bg-blue-50 border-blue-200" },
  MedicationName: { label: "Medicamento", icon: Pill, color: "text-green-700 bg-green-50 border-green-200" },
  AllergyEntity: { label: "Alergia", icon: AlertTriangle, color: "text-red-700 bg-red-50 border-red-200" },
  Symptom: { label: "Sintoma", icon: Stethoscope, color: "text-orange-700 bg-orange-50 border-orange-200" },
};

function EntityBadge({ entity }: { entity: DocumentDetail["medical_entities"][0] }) {
  const meta = CATEGORY_LABELS[entity.category] ?? {
    label: entity.category,
    icon: Stethoscope,
    color: "text-gray-700 bg-gray-50 border-gray-200",
  };
  const Icon = meta.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${meta.color}`}>
      <Icon className="h-3 w-3" />
      <span>{entity.text}</span>
      {entity.normalized_text && entity.normalized_text !== entity.text && (
        <span className="opacity-60">· {entity.normalized_text}</span>
      )}
    </span>
  );
}

interface Props {
  docId: string;
  onClose: () => void;
}

export function DocumentDetail({ docId, onClose }: Props) {
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getDocument(docId)
      .then(setDetail)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [docId]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl bg-white shadow-xl">
        <div className="sticky top-0 flex items-center justify-between border-b border-gray-200 bg-white px-6 py-4">
          <h2 className="font-semibold text-gray-900">
            {detail?.original_name ?? "Detalhes do documento"}
          </h2>
          <button onClick={onClose} className="rounded-md p-1 hover:bg-gray-100">
            <X className="h-5 w-5 text-gray-500" />
          </button>
        </div>

        <div className="space-y-6 p-6">
          {loading && (
            <div className="flex justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
            </div>
          )}

          {error && <p className="text-sm text-red-600">{error}</p>}

          {detail && (
            <>
              {/* Entidades médicas */}
              <div>
                <h3 className="mb-3 text-sm font-semibold text-gray-700">
                  Entidades médicas identificadas ({detail.medical_entities.length})
                </h3>
                {detail.medical_entities.length === 0 ? (
                  <p className="text-sm text-gray-400">Nenhuma entidade médica detectada.</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {detail.medical_entities.map((e, i) => (
                      <EntityBadge key={i} entity={e} />
                    ))}
                  </div>
                )}
              </div>

              {/* Texto extraído */}
              <div>
                <h3 className="mb-3 text-sm font-semibold text-gray-700">Texto extraído</h3>
                <pre className="whitespace-pre-wrap rounded-lg bg-gray-50 border border-gray-200 p-4 text-xs text-gray-700 leading-relaxed">
                  {detail.anonymized_text}
                </pre>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
