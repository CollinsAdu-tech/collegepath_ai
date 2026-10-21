import { SUGGESTIONS } from "../data/suggestions";
import "./SuggestionChips.css";

/**
 * The empty-state "Suggested questions" list (Section 30). When a
 * category chip is selected, this filters down to that category instead
 * of making a backend round trip — pure client-side navigation.
 */
export default function SuggestionChips({ selectedCategory, onSelect }) {
  const items = selectedCategory
    ? SUGGESTIONS.filter((s) => s.category === selectedCategory)
    : SUGGESTIONS;

  if (items.length === 0) {
    return (
      <p className="suggestions__empty">
        No starter questions for this topic yet — ask anything below.
      </p>
    );
  }

  return (
    <ul className="suggestions">
      {items.map((item) => (
        <li key={item.question}>
          <button type="button" className="suggestions__item" onClick={() => onSelect(item.question)}>
            {item.question}
          </button>
        </li>
      ))}
    </ul>
  );
}
