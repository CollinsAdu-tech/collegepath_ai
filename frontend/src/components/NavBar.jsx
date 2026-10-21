import { useEffect, useRef, useState } from "react";
import "./NavBar.css";

function buildCopyText(messages) {
  const lastAnswer = [...messages].reverse().find((m) => m.role === "assistant");
  if (!lastAnswer) return "";
  const parts = [lastAnswer.content];
  if (lastAnswer.source) parts.push(`Source: ${lastAnswer.source}`);
  return parts.join("\n\n");
}

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Fallback for browsers/contexts without the async clipboard API.
    try {
      const area = document.createElement("textarea");
      area.value = text;
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(area);
      return ok;
    } catch {
      return false;
    }
  }
}

export default function NavBar({ messages, loading, onHome, onRefresh, onClear }) {
  const [copied, setCopied] = useState(null); // null | "ok" | "fail"
  const timer = useRef(null);
  const hasChat = messages.length > 0;
  const hasAnswer = messages.some((m) => m.role === "assistant");

  useEffect(() => () => clearTimeout(timer.current), []);

  const handleCopy = async () => {
    const ok = await copyToClipboard(buildCopyText(messages));
    setCopied(ok ? "ok" : "fail");
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setCopied(null), 1800);
  };

  return (
    <nav className="navbar" aria-label="Chat actions">
      <button type="button" className="navbar__btn" onClick={onHome} disabled={loading}>
        Home
      </button>
      <button
        type="button"
        className="navbar__btn"
        onClick={onRefresh}
        disabled={loading}
        title="Re-check the connection and re-ask your last question"
      >
        Refresh
      </button>
      <button
        type="button"
        className="navbar__btn"
        onClick={handleCopy}
        disabled={!hasAnswer}
        title="Copy the latest answer"
      >
        {copied === "ok" ? "Copied ✓" : copied === "fail" ? "Copy failed" : "Copy"}
      </button>
      <button
        type="button"
        className="navbar__btn navbar__btn--danger"
        onClick={onClear}
        disabled={!hasChat || loading}
      >
        Clear
      </button>
      <span className="sr-only" role="status" aria-live="polite">
        {copied === "ok" ? "Answer copied to clipboard" : ""}
      </span>
    </nav>
  );
}
