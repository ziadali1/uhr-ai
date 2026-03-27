import { ChatInterface } from "@/components/chat/ChatInterface";

export default function ChatPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Agente IA</h1>
        <p className="mt-1 text-sm text-gray-500">
          Faça perguntas sobre o histórico médico em linguagem natural. As respostas citam os documentos fonte.
        </p>
      </div>
      <ChatInterface />
    </div>
  );
}
