"use client";

import { useEffect, useState } from "react";
import { getAnalysis, type AnalysisResult } from "@/lib/api";
import {
  Stethoscope, Pill, AlertTriangle, Brain,
  FileText, Loader2, RefreshCw, ChevronRight,
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

export function PatientSummary() {
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    setError("");
    getAnalysis()
      .then(setAnalysis)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-12 text-sm text-gray-500">
        <Loader2 className="h-4 w-4 animate-spin" />
        Analisando histórico médico...
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-8 text-center">
        <FileText className="mx-auto mb-3 h-10 w-10 text-gray-300" />
        <p className="text-sm font-medium text-gray-700">Nenhum documento encontrado</p>
        <p className="mt-1 text-xs text-gray-500">
          Faça upload de documentos médicos para visualizar a análise do histórico.
        </p>
        <Link
          href="/upload"
          className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
        >
          Enviar documentos
          <ChevronRight className="h-4 w-4" />
        </Link>
      </div>
    );
  }

  if (!analysis) return null;

  return (
    <div className="space-y-4">
      {/* Disclaimer */}
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
        <p className="text-xs text-amber-800">
          <strong>Aviso:</strong> {analysis.disclaimer}
        </p>
      </div>

      {/* Resumo do caso */}
      <div className="rounded-xl border border-blue-100 bg-blue-50 p-5">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-blue-900">Resumo do Caso</h3>
          <span className="text-xs text-blue-600">
            {analysis.document_count} documento{analysis.document_count !== 1 ? "s" : ""} analisado{analysis.document_count !== 1 ? "s" : ""}
          </span>
        </div>
        <p className="text-sm text-blue-800 leading-relaxed">{analysis.case_summary}</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {/* Diagnósticos */}
        <Section icon={Stethoscope} title="Diagnósticos Ativos" color="text-blue-600 bg-blue-50">
          {analysis.diagnoses.length === 0 ? (
            <p className="text-xs text-gray-400">Nenhum diagnóstico identificado.</p>
          ) : (
            <ul className="space-y-1.5">
              {analysis.diagnoses.map((d) => (
                <li key={d} className="flex items-center gap-2 text-sm text-gray-700">
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-blue-400" />
                  {d}
                </li>
              ))}
            </ul>
          )}
        </Section>

        {/* Medicamentos */}
        <Section icon={Pill} title="Medicamentos em Uso" color="text-green-600 bg-green-50">
          {analysis.active_medications.length === 0 ? (
            <p className="text-xs text-gray-400">Nenhum medicamento registrado.</p>
          ) : (
            <ul className="space-y-1.5">
              {analysis.active_medications.map((m) => (
                <li key={m} className="flex items-center gap-2 text-sm text-gray-700">
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-green-400" />
                  {m}
                </li>
              ))}
            </ul>
          )}
        </Section>

        {/* Alergias */}
        <Section icon={AlertTriangle} title="Alergias Conhecidas" color="text-red-600 bg-red-50">
          {analysis.allergies.length === 0 ? (
            <p className="text-xs text-gray-400">Nenhuma alergia registrada.</p>
          ) : (
            <ul className="space-y-1.5">
              {analysis.allergies.map((a) => (
                <li key={a} className="flex items-center gap-2 text-sm text-gray-700">
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-red-400" />
                  {a}
                </li>
              ))}
            </ul>
          )}
        </Section>

        {/* Especialidades sugeridas */}
        <Section icon={Brain} title="Especialidades Sugeridas" color="text-purple-600 bg-purple-50">
          {analysis.suggested_specialties.length === 0 ? (
            <p className="text-xs text-gray-400">Nenhuma sugestão disponível.</p>
          ) : (
            <ul className="space-y-3">
              {analysis.suggested_specialties.map((s) => (
                <li key={s.specialty}>
                  <p className="text-sm font-medium text-gray-800">{s.specialty}</p>
                  <p className="text-xs text-gray-500 leading-relaxed">{s.reason}</p>
                </li>
              ))}
            </ul>
          )}
        </Section>
      </div>

      <button
        onClick={load}
        className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 transition-colors"
      >
        <RefreshCw className="h-3 w-3" />
        Atualizar análise
      </button>
    </div>
  );
}
