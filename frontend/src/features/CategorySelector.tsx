import {
  PRIMARY_DESIGN_CATEGORIES,
  type PrimaryCategoryId,
} from "../domain/designCategories";

interface CategorySelectorProps {
  readonly selectedCategory: PrimaryCategoryId | null;
  readonly onSelect: (category: PrimaryCategoryId) => void;
}

export function CategorySelector({ selectedCategory, onSelect }: CategorySelectorProps) {
  return (
    <div className="category-grid" aria-label="Primary design categories">
      {PRIMARY_DESIGN_CATEGORIES.map((category) => (
        <button
          className="category-card"
          type="button"
          key={category.id}
          aria-pressed={selectedCategory === category.id}
          aria-describedby={`${category.id}-description`}
          onClick={() => {
            onSelect(category.id);
          }}
        >
          <span className="category-status" aria-hidden="true">
            {selectedCategory === category.id ? "Selected" : "Select"}
          </span>
          <strong>{category.name}</strong>
          <span id={`${category.id}-description`}>{category.description}</span>
        </button>
      ))}
    </div>
  );
}
