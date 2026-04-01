"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Loader2, FileText, Bot, User } from "lucide-react";
import { chatStream, type ChatMessage } from "@/lib/api";
import { cn } from "@/lib/utils";

const SUGGESTED_QUESTIONS = [
  "Quais medicamentos o paciente usa atualmente?",
  "O paciente tem alguma alergia registrada?",
  "Quais são os diagnósticos ativos?",
  "Qual o tipo sanguíneo do paciente?",
];

export function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage(text: string) {
    if (!text.trim() || isStreaming) return;

    const userMsg: ChatMessage = { role: "user", content: text };
    const history = [...messages];
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsStreaming(true);

    // Adiciona mensagem do assistente vazia para streaming
    const assistantMsg: ChatMessage = { role: "assistant", content: "", sources: [] };
    setMessages((prev) => [...prev, assistantMsg]);

    await chatStream(text, history, {
      onSources: (sources) => {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = { ...updated[updated.length - 1], sources };
          return updated;
        });
      },
      onToken: (token) => {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            content: updated[updated.length - 1].content + token,
          };
          return updated;
        });
      },
      onDone: () => setIsStreaming(false),
      onError: (err) => {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = { ...updated[updated.length - 1], content: err };
          return updated;
        });
        setIsStreaming(false);
      },
    });
  }

  return (
    <div className="flex h-[calc(100vh-10rem)] flex-col rounded-xl border border-gray-200 bg-white overflow-hidden">
      {/* Histórico */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-6 text-center">
            <div className="rounded-full bg-blue-50 p-4">
              <Bot className="h-8 w-8 text-blue-600" />
            </div>
            <div>
              <p className="font-medium text-gray-800">Agente IA — Histórico Médico</p>
              <p className="mt-1 text-sm text-gray-500">
                Faça perguntas sobre os documentos médicos enviados.
                <br />As respostas citam as fontes dos dados.
              </p>
            </div>
            <div className="grid gap-2 w-full max-w-md">
              {SUGGESTED_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => sendMessage(q)}
                  className="rounded-lg border border-gray-200 px-4 py-2 text-left text-sm text-gray-600 hover:border-blue-300 hover:bg-blue-50 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={cn("flex gap-3", msg.role === "user" && "flex-row-reverse")}>
            <div className={cn(
              "flex h-7 w-7 shrink-0 items-center justify-center rounded-full",
              msg.role === "user" ? "bg-blue-600" : "bg-gray-100"
            )}>
              {msg.role === "user"
                ? <User className="h-4 w-4 text-white" />
                : <Bot className="h-4 w-4 text-gray-600" />
              }
            </div>

            <div className={cn("max-w-[80%] space-y-1", msg.role === "user" && "items-end")}>
              <div className={cn(
                "rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap",
                msg.role === "user"
                  ? "bg-blue-600 text-white rounded-tr-sm"
                  : "bg-gray-100 text-gray-800 rounded-tl-sm"
              )}>
                {msg.content}
                {msg.role === "assistant" && isStreaming && i === messages.length - 1 && (
                  <span className="ml-1 inline-block h-3 w-0.5 bg-gray-500 animate-pulse" />
                )}
              </div>

              {msg.sources && msg.sources.length > 0 && (
                <div className="flex flex-wrap gap-1 px-1">
                  {msg.sources.map((s) => (
                    <span key={s} className="flex items-center gap-1 text-xs text-gray-400">
                      <FileText className="h-3 w-3" />
                      {s}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage(input)}
            placeholder="Pergunte sobre o histórico médico..."
            disabled={isStreaming}
            className="flex-1 rounded-xl border border-gray-300 px-4 py-2.5 text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 disabled:opacity-50 transition-all"
          />
          <button
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || isStreaming}
            className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {isStreaming
              ? <Loader2 className="h-4 w-4 animate-spin" />
              : <Send className="h-4 w-4" />
            }
          </button>
        </div>
        <p className="mt-2 text-center text-xs text-gray-400">
          As respostas são baseadas nos documentos enviados e não constituem diagnóstico médico.
        </p>
      </div>
    </div>
  );
}
