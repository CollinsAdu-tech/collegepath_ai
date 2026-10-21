import "./RelatedQuestions.css";

/**
 * The guided-exploration list under an answer (Section 32). `label`
 * differs by context — set by the caller — since the same component
 * serves both "you may also want to ask" (confident) and "try one of
 * these instead" (fallback) without duplicating markup.
 */
export default function RelatedQuestions({ questions, label, onSelect }) {
  if (!questions || questions.length === 0) return null;

  return (
    <div className="related">
      <p className="related__label">{label}</p>
      <ul className="related__list">
        {questions.map((question) => (
          <li key={question}>
            <button type="button" className="related__item" onClick={() => onSelect(question)}>
              {question}
              <span aria-hidden="true">›</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
