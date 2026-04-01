"use client";

import type { ImagingReport } from "@/lib/api";
import { AlertTriangle } from "lucide-react";

const URGENCY_STYLES = {
  routine:  { label: "Rotina",   className: "bg-green-50 text-green-700 border-green-200" },
  urgent:   { label: "Urgente",  className: "bg-yellow-50 text-yellow-800 border-yellow-300" },
  critical: { label: "Crítico",  className: "bg-red-100 text-red-800 border-red-300" },
};

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null;
  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-wide text-gray-500">{label}</dt>
      <dd className="mt-0.5 text-sm text-gray-800 whitespace-pre-wrap">{value}</dd>
    </div>
  );
}

interface Props {
  data: ImagingReport;
}

export function ImagingReportView({ data }: Props) {
  const urgencyStyle = data.urgency ? URGENCY_STYLES[data.urgency] : null;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-3">
        {data.modality && (
          <span className="rounded-full bg-purple-100 px-3 py-1 text-xs font-semibold text-purple-800">
            {data.modality}
          </span>
        )}
        {data.body_region && (
          <span className="text-sm text-gray-600">{data.body_region}</span>
        )}
        {urgencyStyle && (
          <span className={`flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${urgencyStyle.className}`}>
            {data.urgency === "critical" && <AlertTriangle className="h-3 w-3" />}
            {urgencyStyle.label}
          </span>
        )}
      </div>

      {/* Summary */}
      {data.summary && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
          <span className="font-semibold">Resumo clínico: </span>{data.summary}
        </div>
      )}

      <dl className="space-y-3">
        <Field label="Indicação" value={data.indication} />
        <Field label="Achados" value={data.findings} />
        <Field label="Impressão diagnóstica" value={data.impression} />
        <Field label="Recomendações" value={data.recommendations} />
        <Field label="Comparação com estudo anterior" value={data.comparison_with_prior} />
      </dl>
    </div>
  );
}
