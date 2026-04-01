"use client";

import { useEffect, useState } from "react";
import { Pill, MessageSquare, AlertTriangle, Loader2 } from "lucide-react";
import {
  listHealthEntries,
  createHealthEntry,
  deleteHealthEntry,
  type HealthEntry,
  type HealthEntryCreate,
} from "@/lib/api";
import { AddEntryForm } from "@/components/health/AddEntryForm";
import { HealthEntryList } from "@/components/health/HealthEntryList";

type Tab = "medication_current" | "complaint" | "allergy";

const TABS: { id: Tab; label: string; icon: React.ElementType }[] = [
  { id: "medication_current", label: "Medicamentos em uso", icon: Pill },
  { id: "complaint",          label: "Queixas recentes",   icon: MessageSquare },
  { id: "allergy",            label: "Alergias",           icon: AlertTriangle },
];

const TAB_CONFIG: Record<Tab, { placeholder: string; detailsPlaceholder?: string; emptyMessage: string }> = {
  medication_current: {
    placeholder: "Nome do medicamento e dose (ex: Metformina 850mg)",
    detailsPlaceholder: "Frequência / indicação (ex: 2x ao dia, diabetes tipo 2)",
    emptyMessage: "Nenhum medicamento em uso registrado.",
  },
  complaint: {
    placeholder: "Descreva a queixa (ex: Cefaleia persistente há 3 dias)",
    detailsPlaceholder: "Detalhes adicionais (intensidade, localização, etc.)",
    emptyMessage: "Nenhuma queixa recente registrada.",
  },
  allergy: {
    placeholder: "Substância / medicamento (ex: Penicilina)",
    detailsPlaceholder: "Tipo de reação (ex: urticária, anafilaxia)",
    emptyMessage: "Nenhuma alergia registrada.",
  },
};

export default function SaudePage() {
  const [activeTab, setActiveTab] = useState<Tab>("medication_current");
  const [entries, setEntries] = useState<HealthEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listHealthEntries()
      .then(setEntries)
      .finally(() => setLoading(false));
  }, []);

  const filtered = entries.filter((e) => e.entry_type === activeTab);
  const config = TAB_CONFIG[activeTab];

  async function handleAdd(entry: HealthEntryCreate) {
    const created = await createHealthEntry(entry);
    setEntries((prev) => [created, ...prev]);
  }

  async function handleDelete(id: string) {
    await deleteHealthEntry(id);
    setEntries((prev) => prev.filter((e) => e.id !== id));
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Saúde</h1>
        <p className="mt-1 text-sm text-gray-500">
          Registre medicamentos em uso, queixas recentes e alergias conhecidas.
          Estas informações ficam disponíveis para o Agente IA.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg border border-gray-200 bg-gray-50 p-1">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
              activeTab === id
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="space-y-3">
        {loading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
          </div>
        ) : (
          <>
            <HealthEntryList
              entries={filtered}
              onDelete={handleDelete}
              emptyMessage={config.emptyMessage}
            />
            <AddEntryForm
              entryType={activeTab}
              placeholder={config.placeholder}
              detailsPlaceholder={config.detailsPlaceholder}
              onSave={handleAdd}
            />
          </>
        )}
      </div>
    </div>
  );
}
