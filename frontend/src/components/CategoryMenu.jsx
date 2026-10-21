import { useEffect, useState } from "react";
import { getCategories } from "../services/api";
import "./CategoryMenu.css";

/**
 * Section 31: category chips for filtering the suggested-questions list.
 * Reads the live category list from GET /categories (rather than a
 * hardcoded copy) so it never drifts from the knowledge base, but fails
 * silently to an empty row if the backend is unreachable — this is a
 * navigation nicety, not something worth blocking the page over.
 */
export default function CategoryMenu({ selected, onSelect }) {
  const [categories, setCategories] = useState([]);

  useEffect(() => {
    let cancelled = false;
    getCategories().then((data) => {
      if (!cancelled) setCategories(data);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  if (categories.length === 0) return null;

  return (
    <div className="category-menu" role="group" aria-label="Filter by topic">
      {categories.map((category) => {
        const isActive = category === selected;
        return (
          <button
            key={category}
            type="button"
            aria-pressed={isActive}
            className={`category-menu__chip${isActive ? " category-menu__chip--active" : ""}`}
            onClick={() => onSelect(isActive ? null : category)}
          >
            {category}
          </button>
        );
      })}
    </div>
  );
}
