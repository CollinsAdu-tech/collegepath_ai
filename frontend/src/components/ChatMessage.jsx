import RelatedQuestions from "./RelatedQuestions";
import SourceCard from "./SourceCard";
import FeedbackButtons from "./FeedbackButtons";
import "./ChatMessage.css";

/**
 * Renders one turn of the conversation. User turns are plain chat
 * bubbles (Section 29: right-aligned). Assistant turns are NOT bubbles —
 * they're structured "reference cards" (status dot, category, answer,
 * citation footer, related questions), because every assistant reply
 * here carries structured, checkable data a plain bubble can't hold
 * well. Three assistant variants share one card shell: a confident
 * answer, a retrieval fallback, and a connection/API error.
 */
export default function ChatMessage({ message, onSelectRelated }) {
  if (message.role === "user") {
    return (
      <div className="msg-row msg-row--user">
        <div className="bubble">{message.content}</div>
      </div>
    );
  }

  const variant = message.kind; // "answer" | "fallback" | "error"

  return (
    <div className="msg-row msg-row--assistant">
      <div className={`answer-card answer-card--${variant}`}>
        <div className="answer-card__meta">
          <span className={`status-dot status-dot--${variant}`} aria-hidden="true" />
          {message.category && <span className="category-pill">{message.category}</span>}
        </div>

        <p className="answer-card__text">{message.content}</p>

        {variant === "answer" && (
          <>
            <SourceCard
              source={message.source}
              verificationDate={message.verificationDate}
              requiresVerification={message.requiresCurrentVerification}
            />
            <RelatedQuestions
              questions={message.relatedQuestions}
              label="You may also want to ask"
              onSelect={onSelectRelated}
            />
            <FeedbackButtons />
          </>
        )}

        {variant === "fallback" && (
          <RelatedQuestions
            questions={message.relatedQuestions}
            label="Try one of these instead"
            onSelect={onSelectRelated}
          />
        )}
      </div>
    </div>
  );
}
