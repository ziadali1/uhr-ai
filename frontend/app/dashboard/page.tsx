import Link from "next/link";
import { Upload, MessageSquare, QrCode, Brain } from "lucide-react";

const pillars = [
  {
    icon: Upload,
    title: "Documentos",
    description: "Faça upload de laudos, receitas e exames. OCR + anonimização automáticos.",
    href: "/upload",
    color: "text-blue-600 bg-blue-50",
  },
  {
    icon: Brain,
    title: "Análise IA",
    description: "Extração de diagnósticos, medicamentos, alergias e padrões do histórico.",
    href: "/dashboard",
    color: "text-purple-600 bg-purple-50",
    disabled: true,
    badge: "Fase 3",
  },
  {
    icon: MessageSquare,
    title: "Agente IA",
    description: "Tire dúvidas sobre seu histórico em linguagem natural, com citação de fontes.",
    href: "/chat",
    color: "text-green-600 bg-green-50",
    disabled: true,
    badge: "Fase 2",
  },
  {
    icon: QrCode,
    title: "Emergência",
    description: "Relatório crítico com alergias, medicamentos e condições ativas via QR Code.",
    href: "/emergency/local-dev-user-001",
    color: "text-red-600 bg-red-50",
    disabled: true,
    badge: "Fase 4",
  },
];

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Painel</h1>
        <p className="mt-1 text-sm text-gray-500">
          Seu histórico médico centralizado e analisado por IA.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {pillars.map(({ icon: Icon, title, description, href, color, disabled, badge }) => (
          <Link
            key={title}
            href={disabled ? "#" : href}
            className={`group relative rounded-xl border border-gray-200 bg-white p-6 transition-shadow hover:shadow-md ${
              disabled ? "opacity-60 cursor-not-allowed" : "hover:border-blue-300"
            }`}
            onClick={disabled ? (e) => e.preventDefault() : undefined}
          >
            {badge && (
              <span className="absolute right-4 top-4 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-500">
                {badge}
              </span>
            )}
            <div className={`mb-4 inline-flex rounded-lg p-2.5 ${color}`}>
              <Icon className="h-5 w-5" />
            </div>
            <h2 className="font-semibold text-gray-900">{title}</h2>
            <p className="mt-1 text-sm text-gray-500">{description}</p>
          </Link>
        ))}
      </div>

      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
        <p className="text-xs text-amber-800">
          <strong>Aviso legal:</strong> As sugestões geradas pela IA não constituem diagnóstico
          médico. Toda informação deve ser validada por um profissional de saúde habilitado.
          Este projeto é estritamente educacional e de portfólio.
        </p>
      </div>
    </div>
  );
}
