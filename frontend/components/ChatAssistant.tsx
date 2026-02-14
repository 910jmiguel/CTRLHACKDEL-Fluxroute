"use client";

import { useState, useRef, useEffect } from "react";
import { MessageCircle, X, Send, Bot, User } from "lucide-react";
import { useChat } from "@/hooks/useChat";

export default function ChatAssistant() {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const { messages, loading, suggestedActions, sendMessage } = useChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    if (!input.trim() || loading) return;
    sendMessage(input.trim());
    setInput("");
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-600/30 flex items-center justify-center transition-all hover:scale-105"
      >
        <MessageCircle className="w-6 h-6" />
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 w-96 h-[500px] glass-card flex flex-col shadow-2xl slide-up">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-[var(--border)]">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-blue-400" />
          <span className="text-sm font-semibold">FluxRoute AI</span>
          <span className="w-2 h-2 bg-emerald-400 rounded-full" />
        </div>
        <button
          onClick={() => setIsOpen(false)}
          className="text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.length === 0 && (
          <div className="text-center text-[var(--text-muted)] text-sm mt-8">
            <Bot className="w-8 h-8 mx-auto mb-2 text-[var(--text-muted)]" />
            <p>Hi! I&apos;m your FluxRoute assistant.</p>
            <p className="mt-1">Ask me about routes, delays, or transit tips.</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex gap-2 ${
              msg.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            {msg.role === "assistant" && (
              <Bot className="w-5 h-5 text-blue-400 mt-1 flex-shrink-0" />
            )}
            <div
              className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-[var(--surface)] text-[var(--text-primary)]"
              }`}
            >
              {msg.content}
            </div>
            {msg.role === "user" && (
              <User className="w-5 h-5 text-[var(--text-secondary)] mt-1 flex-shrink-0" />
            )}
          </div>
        ))}

        {loading && (
          <div className="flex gap-2">
            <Bot className="w-5 h-5 text-blue-400 mt-1" />
            <div className="bg-[var(--surface)] rounded-lg px-3 py-2">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-[var(--text-muted)] rounded-full animate-bounce" />
                <div
                  className="w-2 h-2 bg-[var(--text-muted)] rounded-full animate-bounce"
                  style={{ animationDelay: "0.15s" }}
                />
                <div
                  className="w-2 h-2 bg-[var(--text-muted)] rounded-full animate-bounce"
                  style={{ animationDelay: "0.3s" }}
                />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick actions */}
      {messages.length === 0 && (
        <div className="px-3 pb-2 flex flex-wrap gap-1.5">
          {suggestedActions.map((action) => (
            <button
              key={action}
              onClick={() => sendMessage(action)}
              className="text-xs px-2.5 py-1 rounded-full bg-[var(--surface)] hover:bg-[var(--surface-hover)] text-[var(--text-secondary)] border border-[var(--border)] transition-colors"
            >
              {action}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="p-3 border-t border-[var(--border)]">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask about routes, delays..."
            className="flex-1 bg-[var(--input-bg)] rounded-lg px-3 py-2 text-sm outline-none border border-[var(--border)] focus:border-blue-500/50 placeholder:text-[var(--text-muted)]"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="p-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-[var(--surface)] disabled:text-[var(--text-muted)] text-white transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
