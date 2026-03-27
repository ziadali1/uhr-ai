export default function ChatPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Agente IA</h1>
        <p className="mt-1 text-sm text-gray-500">
          Faça perguntas sobre seu histórico médico em linguagem natural.
        </p>
      </div>

      <div className="flex h-64 items-center justify-center rounded-xl border-2 border-dashed border-gray-200 bg-white">
        <p className="text-sm text-gray-400">
          Agente IA disponível na Fase 2 — RAG e integração com Azure AI Foundry
        </p>
      </div>
    </div>
  );
}
