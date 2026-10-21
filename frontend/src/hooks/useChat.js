import { useCallback, useRef, useState } from "react";
import { ApiError, sendMessage as sendMessageToApi } from "../services/api";

let nextId = 1;

/**
 * Owns the chat's entire state (Section 54): messages, loading, error,
 * selectedCategory. Exposes sendMessage() as the single entry point for
 * sending a query, whether it came from the text input, a suggestion
 * chip, or a related-question click.
 */
export function useChat() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState(null);

  // A ref (not state) guards against duplicate submits fired within the
  // same tick, before React has re-rendered with loading=true.
  const inFlight = useRef(false);

  const sendMessage = useCallback(async (rawText, { replaceLast = false } = {}) => {
    const text = rawText.trim();
    if (!text || inFlight.current) return;

    inFlight.current = true;
    setLoading(true);

    if (replaceLast) {
      // Drop the previous assistant reply (and its user turn) so a
      // refresh re-asks the same question instead of duplicating it.
      setMessages((prev) => {
        const idx = prev.map((m) => m.role).lastIndexOf("user");
        const kept = idx === -1 ? prev : prev.slice(0, idx);
        return [...kept, { id: nextId++, role: "user", content: text }];
      });
    } else {
      setMessages((prev) => [
        ...prev,
        { id: nextId++, role: "user", content: text },
      ]);
    }

    try {
      const response = await sendMessageToApi(text);
      setMessages((prev) => [
        ...prev,
        {
          id: nextId++,
          role: "assistant",
          kind: response.fallback ? "fallback" : "answer",
          content: response.answer,
          matchedQuestion: response.matched_question,
          category: response.category,
          source: response.source,
          verificationDate: response.verification_date,
          relatedQuestions: response.related_questions ?? [],
          requiresCurrentVerification: response.requires_current_verification,
        },
      ]);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "I couldn't connect to CollegePath AI right now. Please check your connection and try again.";
      setMessages((prev) => [
        ...prev,
        { id: nextId++, role: "assistant", kind: "error", content: message },
      ]);
    } finally {
      inFlight.current = false;
      setLoading(false);
    }
  }, []);

  /** Wipe the conversation (keeps the selected category). */
  const clearChat = useCallback(() => {
    if (inFlight.current) return;
    setMessages([]);
  }, []);

  /** Back to the landing view: empty chat and no category filter. */
  const goHome = useCallback(() => {
    if (inFlight.current) return;
    setMessages([]);
    setSelectedCategory(null);
  }, []);

  /** Re-ask the most recent question and replace its answer. */
  const refreshLast = useCallback(() => {
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    if (lastUser) sendMessage(lastUser.content, { replaceLast: true });
  }, [messages, sendMessage]);

  return {
    clearChat,
    goHome,
    refreshLast,
    messages,
    loading,
    selectedCategory,
    setSelectedCategory,
    sendMessage,
  };
}
