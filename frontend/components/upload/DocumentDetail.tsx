"use client";

import { useEffect, useState } from "react";
import { getDocument, type DocumentDetail, type StructuredLab, type ImagingReport, type ClinicalNote, type MedicationDocument } from "@/lib/api";
import { Loader2, Pill, Stethoscope, AlertTriangle, X, FileText } from "lucide-react";
import { LabFindingsTable } from "./LabFindingsTable";
import { ImagingReportView } from "./ImagingReportView";

const FAMILY_LABELS: Record<string, string> = {
  structured_lab:      "Exame laboratorial",
  imaging_narrative:   "Laudo de imagem",
  clinical_narrative:  "Nota clínica",
  medication_document: "Prescrição / Medicamentos",
  unknown:             "Documento médico",
};

const CATEGORY_LABELS: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  Diagnosis:        { label: "Diagnóstico",   icon: Stethoscope, color: "text-blue-700 bg-blue-50 border-blue-200" },
  MedicationName:   { label: "Medicamento",   icon: Pill,        color: "text-green-700 bg-green-50 border-green-200" },
  AllergyEntity:    { label: "Alergia",       icon: AlertTriangle, color: "text-red-700 bg-red-50 border-red-200" },
  SymptomOrSign:    { label: "Sintoma",       icon: Stethoscope, color: "text-orange-700 bg-orange-50 border-orange-200" },
  LabFinding:       { label: "Achado lab.",   icon: FileText,    color: "text-purple-700 bg-purple-50 border-purple-200" },
  ImagingImpression:{ label: "Imagem",        icon: FileText,    color: "text-indigo-700 bg-indigo-50 border-indigo-200" },
  ImagingFinding:   { label: "Achado imagem", icon: FileText,    color: "text-indigo-700 bg-indigo-50 border-indigo-200" },
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

function ClinicalNoteView({ data }: { data: ClinicalNote }) {
  return (
    <div className="space-y-3 text-sm">
      {data.summary && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-blue-800">
          <span className="font-semibold">Resumo: </span>{data.summary}
        </div>
      )}
      {data.chief_complaint && (
        <div><span className="font-semibold text-gray-700">Queixa principal: </span>{data.chief_complaint}</div>
      )}
      {data.diagnoses.length > 0 && (
        <div>
          <span className="font-semibold text-gray-700">Diagnósticos: </span>
          <ul className="ml-4 mt-1 list-disc text-gray-600">{data.diagnoses.map((d, i) => <li key={i}>{d}</li>)}</ul>
        </div>
      )}
      {data.suspected_diagnoses.length > 0 && (
        <div>
          <span className="font-semibold text-gray-700">Hipóteses diagnósticas: </span>
          <ul className="ml-4 mt-1 list-disc text-gray-600">{data.suspected_diagnoses.map((d, i) => <li key={i}>{d}</li>)}</ul>
        </div>
      )}
      {data.symptoms.length > 0 && (
        <div>
          <span className="font-semibold text-gray-700">Sintomas: </span>
          <span className="text-gray-600">{data.symptoms.join(", ")}</span>
        </div>
      )}
      {data.allergies.length > 0 && (
        <div>
          <span className="font-semibold text-red-700">Alergias: </span>
          <span className="text-red-600">{data.allergies.join(", ")}</span>
        </div>
      )}
      {data.medications.length > 0 && (
        <div>
          <span className="font-semibold text-gray-700">Medicamentos: </span>
          <ul className="ml-4 mt-1 list-disc text-gray-600">{data.medications.map((m, i) => <li key={i}>{m}</li>)}</ul>
        </div>
      )}
      {data.conduct && (
        <div><span className="font-semibold text-gray-700">Conduta: </span>{data.conduct}</div>
      )}
      {data.follow_up && (
        <div><span className="font-semibold text-gray-700">Retorno: </span>{data.follow_up}</div>
      )}
    </div>
  );
}

function MedicationDocumentView({ data }: { data: MedicationDocument }) {
  return (
    <div className="space-y-3">
      {data.summary && (
        <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
          {data.summary}
        </div>
      )}
      {data.medications.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-semibold text-gray-600">
                <th className="px-3 py-2">Medicamento</th>
                <th className="px-3 py-2">Dose / Via</th>
                <th className="px-3 py-2">Posologia</th>
                <th className="px-3 py-2">Indicação</th>
              </tr>
            </thead>
            <tbody>
              {data.medications.map((m, i) => (
                <tr key={i} className="border-b border-gray-100 last:border-0">
                  <td className="px-3 py-2 font-medium text-gray-800">{m.name}</td>
                  <td className="px-3 py-2 text-gray-600">
                    {[m.dose, m.route].filter(Boolean).join(" · ") || "—"}
                  </td>
                  <td className="px-3 py-2 text-gray-600">
                    {[m.frequency, m.duration].filter(Boolean).join(", ") || "—"}
                  </td>
                  <td className="px-3 py-2 text-gray-500">{m.indication ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function StructuredView({ detail }: { detail: DocumentDetail }) {
  const sr = detail.structured_result;
  if (!sr) return null;

  const family = sr.document_family;
  const sd = sr.structured_data as Record<string, unknown>;

  return (
    <div>
      <div className="mb-3 flex items-center gap-2">
        <h3 className="text-sm font-semibold text-gray-700">
          {FAMILY_LABELS[family] ?? "Resultado estruturado"}
        </h3>
        {sr.extraction_confidence > 0 && (
          <span className="text-xs text-gray-400">
            (confiança: {Math.round(sr.extraction_confidence * 100)}%)
          </span>
        )}
      </div>

      {family === "structured_lab" && sd && (
        <LabFindingsTable data={sd as unknown as StructuredLab} />
      )}
      {family === "imaging_narrative" && sd && (
        <ImagingReportView data={sd as unknown as ImagingReport} />
      )}
      {family === "clinical_narrative" && sd && (
        <ClinicalNoteView data={sd as unknown as ClinicalNote} />
      )}
      {family === "medication_document" && sd && (
        <MedicationDocumentView data={sd as unknown as MedicationDocument} />
      )}
    </div>
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

  const hasStructuredResult = detail?.structured_result?.document_family &&
    detail.structured_result.document_family !== "unknown" &&
    Object.keys(detail.structured_result.structured_data ?? {}).length > 0;

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
              {/* Structured result (primary view) */}
              {hasStructuredResult && (
                <StructuredView detail={detail} />
              )}

              {/* Entities (fallback or supplement) */}
              {detail.medical_entities.length > 0 && (
                <div>
                  <h3 className="mb-3 text-sm font-semibold text-gray-700">
                    {hasStructuredResult ? "Achados para memória do paciente" : "Entidades clínicas identificadas"} ({detail.medical_entities.length})
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {detail.medical_entities.map((e, i) => (
                      <EntityBadge key={i} entity={e} />
                    ))}
                  </div>
                </div>
              )}

              {/* Raw extracted text */}
              <details>
                <summary className="cursor-pointer select-none text-xs font-semibold uppercase tracking-wide text-gray-400 hover:text-gray-600">
                  Texto extraído (OCR) ▸
                </summary>
                <pre className="mt-2 whitespace-pre-wrap rounded-lg border border-gray-200 bg-gray-50 p-4 text-xs text-gray-700 leading-relaxed">
                  {detail.anonymized_text}
                </pre>
              </details>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
