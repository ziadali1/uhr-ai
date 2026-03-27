"use client";

import { useEffect, useState } from "react";
import {
  getEmergencyProfile,
  emergencyPdfUrl,
  emergencyQrUrl,
  type EmergencyProfile,
} from "@/lib/api";
import { AlertTriangle, Pill, Stethoscope, Printer, Loader2, QrCode } from "lucide-react";

const SEVERITY_STYLE: Record<string, string> = {
  severa: "border-red-400 bg-red-50 text-red-800 font-bold",
  moderada: "border-orange-300 bg-orange-50 text-orange-800",
  leve: "border-yellow-300 bg-yellow-50 text-yellow-800",
};

export default function EmergencyPage({ params }: { params: { userId: string } }) {
  const { userId } = params;
  const [profile, setProfile] = useState<EmergencyProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getEmergencyProfile(userId)
      .then(setProfile)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [userId]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-red-50">
        <Loader2 className="h-8 w-8 animate-spin text-red-500" />
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-red-50 p-6 text-center">
        <div className="rounded-full bg-red-100 p-4">
          <AlertTriangle className="h-10 w-10 text-red-500" />
        </div>
        <h1 className="text-xl font-bold text-red-900">Perfil não encontrado</h1>
        <p className="max-w-sm text-sm text-red-700">
          {error || "Nenhum documento médico foi enviado para este usuário."}
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-red-50 p-4">
      <div className="mx-auto max-w-md space-y-4">

        {/* Header */}
        <div className="rounded-2xl bg-red-600 px-6 py-5 text-white shadow-lg">
          <div className="flex items-center gap-2 text-2xl font-black tracking-wide">
            🚨 EMERGÊNCIA
          </div>
          <p className="mt-1 text-sm text-red-200">
            Unified Health Record — Informações médicas críticas
          </p>
          {profile.blood_type && (
            <div className="mt-3 inline-flex items-center gap-2 rounded-full bg-white/20 px-4 py-1.5 text-sm font-bold">
              🩸 Tipo Sanguíneo: {profile.blood_type}
            </div>
          )}
        </div>

        {/* Alergias */}
        {profile.allergies.length > 0 && (
          <div className="rounded-2xl border border-red-200 bg-white p-5 shadow-sm">
            <div className="mb-3 flex items-center gap-2 text-red-700">
              <AlertTriangle className="h-5 w-5" />
              <h2 className="font-bold uppercase tracking-wide text-sm">Alergias</h2>
            </div>
            <ul className="space-y-2">
              {profile.allergies.map((a) => (
                <li
                  key={a.name}
                  className={`flex items-center justify-between rounded-lg border px-3 py-2 text-sm ${SEVERITY_STYLE[a.severity] ?? SEVERITY_STYLE.moderada}`}
                >
                  <span>• {a.name}</span>
                  <span className="text-xs uppercase tracking-wider opacity-75">{a.severity}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Medicamentos */}
        {profile.active_medications.length > 0 && (
          <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
            <div className="mb-3 flex items-center gap-2 text-green-700">
              <Pill className="h-5 w-5" />
              <h2 className="font-bold uppercase tracking-wide text-sm">Medicamentos em Uso</h2>
            </div>
            <ul className="space-y-3">
              {profile.active_medications.map((m) => (
                <li key={m.name}>
                  <p className="text-sm font-medium text-gray-800">
                    • {m.name} <span className="text-gray-500">{m.dose}</span>
                  </p>
                  {m.alert && (
                    <p className="mt-0.5 ml-3 text-xs font-medium text-orange-600">
                      ⚠ {m.alert}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Condições ativas */}
        {profile.active_conditions.length > 0 && (
          <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
            <div className="mb-3 flex items-center gap-2 text-blue-700">
              <Stethoscope className="h-5 w-5" />
              <h2 className="font-bold uppercase tracking-wide text-sm">Condições Ativas</h2>
            </div>
            <ul className="space-y-1.5">
              {profile.active_conditions.map((c) => (
                <li key={c} className="text-sm text-gray-800">• {c}</li>
              ))}
            </ul>
          </div>
        )}

        {/* QR Code + ações */}
        <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-4">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={emergencyQrUrl(userId)}
              alt="QR Code de emergência"
              className="h-24 w-24 rounded-lg border border-gray-100"
            />
            <div className="flex-1 space-y-2">
              <p className="text-xs text-gray-500">
                Escaneie para acessar este perfil de emergência
              </p>
              <a
                href={emergencyPdfUrl(userId)}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700 transition-colors"
              >
                <Printer className="h-4 w-4" />
                Baixar cartão PDF
              </a>
            </div>
          </div>
        </div>

        {/* Rodapé */}
        <p className="text-center text-xs text-gray-400 pb-4">
          Atualizado em{" "}
          {new Date(profile.last_updated).toLocaleDateString("pt-BR", {
            day: "2-digit", month: "2-digit", year: "numeric",
            hour: "2-digit", minute: "2-digit",
          })}
        </p>
      </div>
    </div>
  );
}
