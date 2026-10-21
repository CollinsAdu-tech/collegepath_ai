import { useState } from "react";
import "./FeedbackButtons.css";

/**
 * Section 33: frontend-only for now — no backend call, just local state.
 * Architected so a future POST /feedback call would slot into onPick
 * without touching the rest of the component.
 */
export default function FeedbackButtons() {
  const [picked, setPicked] = useState(null);

  if (picked) {
    return <p className="feedback feedback--done">Thanks for the feedback.</p>;
  }

  return (
    <div className="feedback">
      <span className="feedback__label">Helpful?</span>
      <button
        type="button"
        className="feedback__btn"
        aria-label="This answer was helpful"
        onClick={() => setPicked("up")}
      >
        👍
      </button>
      <button
        type="button"
        className="feedback__btn"
        aria-label="This answer was not helpful"
        onClick={() => setPicked("down")}
      >
        👎
      </button>
    </div>
  );
}
