"use client";

import { useState, useCallback } from "react";
import type { ChatMessage } from "@/lib/types";
import { sendChatMessage } from "@/lib/api";

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [suggestedActions, setSuggestedActions] = useState<string[]>([
    "Plan a route",
    "Check delays on Line 1",
    "How's the weather?",
  ]);

  const sendMessage = useCallback(
    async (text: string, context?: Record<string, unknown>) => {
      const userMsg: ChatMessage = { role: "user", content: text };
      setMessages((prev) => [...prev, userMsg]);
      setLoading(true);

      try {
        const response = await sendChatMessage(
          text,
          [...messages, userMsg],
          context
        );

        const assistantMsg: ChatMessage = {
          role: "assistant",
          content: response.message,
        };
        setMessages((prev) => [...prev, assistantMsg]);

        if (response.suggested_actions.length > 0) {
          setSuggestedActions(response.suggested_actions);
        }
      } catch {
        const errorMsg: ChatMessage = {
          role: "assistant",
          content:
            "Sorry, I'm having trouble connecting. The route planner and other features still work — try using them directly!",
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setLoading(false);
      }
    },
    [messages]
  );

  const clearChat = useCallback(() => {
    setMessages([]);
  }, []);

  return {
    messages,
    loading,
    suggestedActions,
    sendMessage,
    clearChat,
  };
}
