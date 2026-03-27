"use client";

import { useState, useCallback } from "react";
import { Upload, FileText, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { uploadDocument } from "@/lib/api";
import { cn } from "@/lib/utils";

type UploadStatus = "idle" | "uploading" | "success" | "error";

interface UploadResult {
  document_id: string;
  message: string;
  entity_count: number;
}

export function UploadZone({ onSuccess }: { onSuccess?: () => void }) {
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [isDragging, setIsDragging] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string>("");

  const handleFile = useCallback(async (file: File) => {
    setStatus("uploading");
    setResult(null);
    setError("");

    try {
      const data = await uploadDocument(file);
      setResult(data);
      setStatus("success");
      onSuccess?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro desconhecido");
      setStatus("error");
    }
  }, [onSuccess]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div className="space-y-4">
      <label
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={cn(
          "flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-10 cursor-pointer transition-colors",
          isDragging
            ? "border-blue-500 bg-blue-50"
            : "border-gray-300 bg-gray-50 hover:border-blue-400 hover:bg-blue-50/50"
        )}
      >
        <Upload className="h-10 w-10 text-gray-400" />
        <div className="text-center">
          <p className="text-sm font-medium text-gray-700">
            Arraste um documento médico ou clique para selecionar
          </p>
          <p className="mt-1 text-xs text-gray-500">
            PDF, JPEG, PNG ou TIFF — máximo 10MB
          </p>
        </div>
        <input
          type="file"
          className="hidden"
          accept=".pdf,.jpg,.jpeg,.png,.tiff,.tif,.webp"
          onChange={handleChange}
          disabled={status === "uploading"}
        />
      </label>

      {/* Status */}
      {status === "uploading" && (
        <div className="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 p-4">
          <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
          <div>
            <p className="text-sm font-medium text-blue-800">Processando documento...</p>
            <p className="text-xs text-blue-600">OCR → extração de entidades → anonimização</p>
          </div>
        </div>
      )}

      {status === "success" && result && (
        <div className="flex items-start gap-3 rounded-lg border border-green-200 bg-green-50 p-4">
          <CheckCircle className="h-5 w-5 shrink-0 text-green-600 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-green-800">Documento processado com sucesso</p>
            <p className="text-xs text-green-700 mt-1">{result.message}</p>
            <p className="text-xs text-green-600 mt-1">
              <FileText className="inline h-3 w-3 mr-1" />
              {result.entity_count} entidades médicas identificadas
            </p>
          </div>
        </div>
      )}

      {status === "error" && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-4">
          <AlertCircle className="h-5 w-5 shrink-0 text-red-600" />
          <div>
            <p className="text-sm font-medium text-red-800">Erro ao processar documento</p>
            <p className="text-xs text-red-600">{error}</p>
          </div>
        </div>
      )}
    </div>
  );
}
