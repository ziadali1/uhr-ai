"use client";

import { useEffect, useState } from "react";
import {
  getPatientSummary,
  type PatientSummaryResponse,
} from "@/lib/api";
import {
  Stethoscope,
  Pill,
  AlertTriangle,
  FlaskConical,
  Loader2,
  FileText,
  RefreshCw,
  ChevronRight,
} from "lucide-react";
import Link from "next/link";

function Section({
  icon: Icon,
  title,
  color,
  children,
}: {
  icon: React.ElementType;
  title: string;
  color: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <div className="mb-3 flex items-center gap-2">
        <div className={`rounded-lg p-1.5 ${color}`}>
          <Icon className="h-4 w-4" />
        </div>
        <h3 className="text-sm font-semibold text-gray-800">{title}</h3>
      </div>
      {children}
    </div>
  );
}

function flagClasses(flag: string | null): string | null {
  if (!flag) return null;
  const upper = flag.toUpperCase();
  if (upper === "H" || upper === "HH" || upper === "HIGH" || upper === "CRITICAL") return "bg-red-100 text-red-700";
  if (upper === "L" || upper === "LL" || upper === "LOW") return "bg-blue-100 text-blue-700";
  return null;
}

export function PatientStructuredData() {
  const [data, setData] = useState<PatientSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    setError("");
    getPatientSummary()
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-12 text-sm text-gray-500">
        <Loader2 className="h-4 w-4 animate-spin" />
        Carregando dados clínicos...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-8 text-center">
        <FileText className="mx-auto mb-3 h-10 w-10 text-gray-300" />
        <p className="text-sm font-semibold text-gray-700">Nenhum dado clínico encontrado</p>
        <p className="mt-1 text-xs text-gray-500">
          Faça upload de documentos médicos para visualizar condições, medicamentos e exames.
        </p>
        <Link
          href="/upload"
          className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 transition-colors"
        >
          Enviar documentos
          <ChevronRight className="h-4 w-4" />
        </Link>
      </div>
    );
  }

  const isEmpty =
    data.active_conditions.length === 0 &&
    data.current_medications.length === 0 &&
    data.allergies.length === 0 &&
    data.latest_labs.length === 0;

  if (isEmpty) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-8 text-center">
        <FileText className="mx-auto mb-3 h-10 w-10 text-gray-300" />
        <p className="text-sm font-semibold text-gray-700">Nenhum dado clínico encontrado</p>
        <p className="mt-1 text-xs text-gray-500">
          Faça upload de documentos médicos para visualizar condições, medicamentos e exames.
        </p>
        <Link
          href="/upload"
          className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 transition-colors"
        >
          Enviar documentos
          <ChevronRight className="h-4 w-4" />
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        {/* Condições Ativas */}
        <Section icon={Stethoscope} title="Condições Ativas" color="text-blue-600 bg-blue-50">
          {data.active_conditions.length === 0 ? (
            <p className="text-xs text-gray-400">Nenhuma condição registrada.</p>
          ) : (
            <ul className="space-y-1.5">
              {data.active_conditions.map((c) => (
                <li key={c.normalized_condition} className="flex items-center gap-2 text-sm text-gray-700">
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-blue-400" />
                  {c.normalized_condition}
                </li>
              ))}
            </ul>
          )}
        </Section>

        {/* Medicamentos em Uso */}
        <Section icon={Pill} title="Medicamentos em Uso" color="text-green-600 bg-green-50">
          {data.current_medications.length === 0 ? (
            <p className="text-xs text-gray-400">Nenhum medicamento registrado.</p>
          ) : (
            <ul className="space-y-1.5">
              {data.current_medications.map((m) => (
                <li key={m.normalized_medication} className="flex items-center gap-2 text-sm text-gray-700">
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-green-400" />
                  {m.normalized_medication}
                  {m.dose && <span className="text-xs text-gray-400">{m.dose}</span>}
                </li>
              ))}
            </ul>
          )}
        </Section>

        {/* Alergias Conhecidas */}
        <Section icon={AlertTriangle} title="Alergias Conhecidas" color="text-red-600 bg-red-50">
          {data.allergies.length === 0 ? (
            <p className="text-xs text-gray-400">Nenhuma alergia registrada.</p>
          ) : (
            <ul className="space-y-1.5">
              {data.allergies.map((a) => (
                <li key={a.normalized_allergen} className="flex items-center gap-2 text-sm text-gray-700">
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-red-400" />
                  {a.normalized_allergen}
                  {a.reaction && <span className="text-xs text-gray-400">({a.reaction})</span>}
                </li>
              ))}
            </ul>
          )}
        </Section>

        {/* Últimos Exames */}
        <Section icon={FlaskConical} title="Últimos Exames" color="text-teal-600 bg-teal-50">
          {data.latest_labs.length === 0 ? (
            <p className="text-xs text-gray-400">Nenhum exame registrado.</p>
          ) : (
            <ul className="space-y-0.5">
              {data.latest_labs.map((lab) => (
                <li key={lab.analyte_norm} className="flex items-center justify-between gap-2 py-1">
                  <span className="flex items-center gap-1.5 text-sm text-gray-700">
                    {lab.analyte_norm}
                    {lab.needs_review && (
                      <span
                        className="h-1.5 w-1.5 rounded-full bg-amber-400"
                        title="Valor com conflito de deduplicação — pode requerer revisão"
                      />
                    )}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-gray-900">
                      {lab.value_num ?? lab.value_str} {lab.unit}
                    </span>
                    {flagClasses(lab.flag) && (
                      <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${flagClasses(lab.flag)}`}>
                        {lab.flag}
                      </span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Section>
      </div>

      <button
        onClick={load}
        className="flex items-center gap-1.5 py-2.5 text-xs text-gray-400 hover:text-gray-600 transition-colors"
      >
        <RefreshCw className="h-3 w-3" />
        Atualizar dados
      </button>
    </div>
  );
}
