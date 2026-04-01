"use client";

import { Trash2 } from "lucide-react";
import type { HealthEntry } from "@/lib/api";

interface Props {
  entries: HealthEntry[];
  onDelete: (id: string) => void;
  emptyMessage: string;
}

export function HealthEntryList({ entries, onDelete, emptyMessage }: Props) {
  if (entries.length === 0) {
    return <p className="py-6 text-center text-sm text-gray-400">{emptyMessage}</p>;
  }

  return (
    <ul className="space-y-2">
      {entries.map((entry) => (
        <li
          key={entry.id}
          className="flex items-start justify-between gap-3 rounded-lg border border-gray-200 bg-white px-4 py-3"
        >
          <div className="min-w-0">
            <p className="text-sm font-medium text-gray-800">{entry.name}</p>
            {entry.details && (
              <p className="mt-0.5 text-xs text-gray-500">{entry.details}</p>
            )}
            {entry.started_at && (
              <p className="mt-0.5 text-xs text-gray-400">
                Desde {new Date(entry.started_at).toLocaleDateString("pt-BR")}
              </p>
            )}
          </div>
          <button
            onClick={() => onDelete(entry.id)}
            className="shrink-0 rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500 transition-colors"
            aria-label="Remover"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </li>
      ))}
    </ul>
  );
}
