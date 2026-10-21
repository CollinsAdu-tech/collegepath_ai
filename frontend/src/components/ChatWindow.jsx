import { useEffect, useRef } from "react";
import ChatMessage from "./ChatMessage";
import TypingIndicator from "./TypingIndicator";
import "./ChatWindow.css";

export default function ChatWindow({ messages, loading, onSelectRelated }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, loading]);

  return (
    <div className="chat-window" role="log" aria-live="polite">
      {messages.map((message) => (
        <ChatMessage key={message.id} message={message} onSelectRelated={onSelectRelated} />
      ))}
      {loading && (
        <div className="msg-row msg-row--assistant">
          <TypingIndicator />
        </div>
      )}
      <div ref={endRef} />
    </div>
  );
}
