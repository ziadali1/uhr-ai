"use client";

import { useState } from "react";
import { Plus, Loader2 } from "lucide-react";
import type { HealthEntryCreate, HealthEntryType } from "@/lib/api";

interface Props {
  entryType: HealthEntryType;
  placeholder: string;
  detailsPlaceholder?: string;
  onSave: (entry: HealthEntryCreate) => Promise<void>;
}

export function AddEntryForm({ entryType, placeholder, detailsPlaceholder, onSave }: Props) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [details, setDetails] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    setError("");
    try {
      await onSave({ entry_type: entryType, name: name.trim(), details: details.trim() || undefined });
      setName("");
      setDetails("");
      setOpen(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-1.5 rounded-lg border border-dashed border-gray-300 px-4 py-2.5 text-sm text-gray-500 hover:border-blue-400 hover:text-blue-600 transition-colors w-full"
      >
        <Plus className="h-4 w-4" />
        Adicionar
      </button>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-lg border border-blue-200 bg-blue-50 p-4 space-y-3">
      <input
        autoFocus
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-400 focus:outline-none"
      />
      {detailsPlaceholder && (
        <input
          value={details}
          onChange={(e) => setDetails(e.target.value)}
          placeholder={detailsPlaceholder}
          className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-400 focus:outline-none"
        />
      )}
      {error && <p className="text-xs text-red-600">{error}</p>}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={saving || !name.trim()}
          className="flex items-center gap-1.5 rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {saving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
          Salvar
        </button>
        <button
          type="button"
          onClick={() => { setOpen(false); setName(""); setDetails(""); }}
          className="rounded-md px-4 py-1.5 text-sm text-gray-500 hover:bg-gray-100"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
