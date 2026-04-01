"use client";

import type { LabFinding, StructuredLab } from "@/lib/api";

const FLAG_STYLES: Record<string, { label: string; className: string }> = {
  high:       { label: "Alto",      className: "bg-red-100 text-red-800 border-red-300" },
  low:        { label: "Baixo",     className: "bg-blue-100 text-blue-800 border-blue-300" },
  borderline: { label: "Limítrofe", className: "bg-yellow-100 text-yellow-800 border-yellow-300" },
  critical:   { label: "Crítico",   className: "bg-red-200 text-red-900 border-red-400 font-bold" },
  normal:     { label: "Normal",    className: "bg-green-50 text-green-700 border-green-200" },
};

function FlagBadge({ flag }: { flag: LabFinding["flag"] }) {
  if (!flag) return null;
  const style = FLAG_STYLES[flag] ?? FLAG_STYLES.normal;
  return (
    <span className={`inline-block rounded-full border px-2 py-0.5 text-xs font-medium ${style.className}`}>
      {style.label}
    </span>
  );
}

interface Props {
  data: StructuredLab;
}

export function LabFindingsTable({ data }: Props) {
  const actionable = data.findings.filter((f) => f.is_clinically_actionable);
  const normal = data.findings.filter((f) => !f.is_clinically_actionable);

  return (
    <div className="space-y-4">
      {/* Exam header */}
      <div className="flex flex-wrap gap-4 text-sm text-gray-600">
        {data.exam_name && (
          <span><span className="font-medium">Exame:</span> {data.exam_name}</span>
        )}
        {data.sample_type && (
          <span><span className="font-medium">Material:</span> {data.sample_type}</span>
        )}
        {data.collection_date && (
          <span><span className="font-medium">Coleta:</span> {data.collection_date}</span>
        )}
      </div>

      {/* Summary */}
      {data.summary && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
          <span className="font-semibold">Resumo clínico: </span>{data.summary}
        </div>
      )}

      {/* Actionable findings */}
      {actionable.length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
            Achados com atenção clínica ({actionable.length})
          </h4>
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-semibold text-gray-600">
                  <th className="px-3 py-2">Analito</th>
                  <th className="px-3 py-2">Resultado</th>
                  <th className="px-3 py-2">Referência</th>
                  <th className="px-3 py-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {actionable.map((f, i) => (
                  <tr key={i} className="border-b border-gray-100 last:border-0">
                    <td className="px-3 py-2 font-medium text-gray-800">{f.name}</td>
                    <td className="px-3 py-2 text-gray-700">
                      {f.value}{f.unit ? ` ${f.unit}` : ""}
                    </td>
                    <td className="px-3 py-2 text-gray-500">{f.reference_range ?? "—"}</td>
                    <td className="px-3 py-2"><FlagBadge flag={f.flag} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Normal findings (collapsible) */}
      {normal.length > 0 && (
        <details className="group">
          <summary className="cursor-pointer select-none text-xs font-semibold uppercase tracking-wide text-gray-400 hover:text-gray-600">
            Achados dentro da normalidade ({normal.length}) ▸
          </summary>
          <div className="mt-2 overflow-x-auto rounded-lg border border-gray-100">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs text-gray-500">
                  <th className="px-3 py-2">Analito</th>
                  <th className="px-3 py-2">Resultado</th>
                  <th className="px-3 py-2">Referência</th>
                </tr>
              </thead>
              <tbody>
                {normal.map((f, i) => (
                  <tr key={i} className="border-b border-gray-50 last:border-0 text-gray-500">
                    <td className="px-3 py-2">{f.name}</td>
                    <td className="px-3 py-2">{f.value}{f.unit ? ` ${f.unit}` : ""}</td>
                    <td className="px-3 py-2">{f.reference_range ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </div>
  );
}
