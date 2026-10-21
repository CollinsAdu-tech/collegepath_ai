import { useRef, useState } from "react";
import "./ChatInput.css";

export default function ChatInput({ onSend, loading }) {
  const [value, setValue] = useState("");
  const textareaRef = useRef(null);

  function handleSubmit(event) {
    event.preventDefault();
    if (!value.trim() || loading) return;
    onSend(value);
    setValue("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit(event);
    }
  }

  function handleChange(event) {
    setValue(event.target.value);
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
    }
  }

  return (
    <form className="chat-input" onSubmit={handleSubmit}>
      <textarea
        ref={textareaRef}
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder="Ask CollegePath AI…"
        rows={1}
        aria-label="Ask a question"
        disabled={loading}
      />
      <button type="submit" disabled={loading || !value.trim()}>
        Ask
      </button>
    </form>
  );
}
