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

  const sendMessage = useCallback(async (rawText) => {
    const text = rawText.trim();
    if (!text || inFlight.current) return;

    inFlight.current = true;
    setLoading(true);

    setMessages((prev) => [
      ...prev,
      { id: nextId++, role: "user", content: text },
    ]);

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

  return {
    messages,
    loading,
    selectedCategory,
    setSelectedCategory,
    sendMessage,
  };
}
