import React from "react";
import Link from "next/link";
import { Upload, MessageSquare, QrCode, Brain, Activity } from "lucide-react";
import { PatientSummary } from "@/components/dashboard/PatientSummary";
import { PatientStructuredData } from "@/components/dashboard/PatientStructuredData";

const quickLinks: { icon: React.ElementType; title: string; description: string; href: string; color: string; disabled?: boolean; badge?: string }[] = [
  {
    icon: Upload,
    title: "Documentos",
    description: "Enviar laudos, receitas e exames.",
    href: "/upload",
    color: "text-blue-600 bg-blue-50",
  },
  {
    icon: MessageSquare,
    title: "Agente IA",
    description: "Perguntas sobre o histórico.",
    href: "/chat",
    color: "text-green-600 bg-green-50",
  },
  {
    icon: QrCode,
    title: "Emergência",
    description: "Relatório crítico via QR Code.",
    href: "/emergency?userId=local-dev-user-001",
    color: "text-red-600 bg-red-50",
  },
];

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Painel</h1>
          <p className="mt-1 text-sm text-gray-500">
            Histórico médico centralizado e analisado por IA.
          </p>
        </div>
        <div className="flex gap-2">
          {quickLinks.map(({ icon: Icon, title, href, color, disabled, badge }) => (
            <Link
              key={title}
              href={disabled ? "#" : href}
              aria-disabled={disabled}
              title={title}
              className={`relative flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-700 transition-all hover:shadow-sm ${
                disabled ? "opacity-50 pointer-events-none" : "hover:border-blue-300"
              }`}
            >
              <div className={`rounded p-1 ${color}`}>
                <Icon className="h-3.5 w-3.5" />
              </div>
              {title}
              {badge && (
                <span className="ml-1 rounded-full bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-400">
                  {badge}
                </span>
              )}
            </Link>
          ))}
        </div>
      </div>

      {/* Análise do histórico */}
      <div>
        <div className="mb-4 flex items-center gap-2">
          <div className="rounded-lg bg-purple-50 p-1.5 text-purple-600">
            <Brain className="h-4 w-4" />
          </div>
          <h2 className="text-base font-semibold text-gray-800">Análise do Histórico</h2>
        </div>
        <PatientSummary />
      </div>

      {/* Dados Clínicos */}
      <div>
        <div className="mb-4 flex items-center gap-2">
          <div className="rounded-lg bg-teal-50 p-1.5 text-teal-600">
            <Activity className="h-4 w-4" />
          </div>
          <h2 className="text-base font-semibold text-gray-800">Dados Clínicos</h2>
          <p className="text-xs text-gray-500">Informações estruturadas extraídas dos documentos.</p>
        </div>
        <PatientStructuredData />
      </div>
    </div>
  );
}
