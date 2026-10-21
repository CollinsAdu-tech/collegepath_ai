import "./TypingIndicator.css";

export default function TypingIndicator() {
  return (
    <div className="answer-card answer-card--pending" role="status" aria-live="polite">
      <span className="sr-only">CollegePath AI is thinking</span>
      <div className="typing-dots" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
    </div>
  );
}
