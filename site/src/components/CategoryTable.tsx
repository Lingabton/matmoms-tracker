import type { SiteData } from "../hooks/useData";

interface Props {
  data: SiteData;
}

// Show all planned categories even if data is sparse
const ALL_CATEGORIES = [
  "Mjölk", "Ost", "Yoghurt", "Grädde", "Smör & Margarin", "Ägg",
  "Nötkött", "Fläskkött", "Kyckling", "Chark & Pålägg",
  "Fisk & Skaldjur", "Frukt", "Grönsaker", "Frysta grönsaker",
  "Färskt bröd", "Knäckebröd", "Frukost & Flingor",
  "Pasta & Ris", "Mjöl & Socker", "Konserver", "Såser & Kryddor",
  "Olja & Vinäger", "Barnmat", "Färdigrätter",
  "Juice", "Läsk", "Vatten",
  "Choklad", "Godis", "Chips", "Glass",
];

export function CategoryTable({ data }: Props) {
  const { byCategory, isPostCut } = data;

  const catMap = new Map(byCategory.map((c) => [c.category, c]));

  if (isPostCut) {
    const sorted = [...byCategory].sort(
      (a, b) => (b.passThroughPercent ?? 0) - (a.passThroughPercent ?? 0)
    );

    return (
      <div className="card" id="kategori">
        <h2>
          Per produktkategori
          <span className="subtitle">
            Genomslag av momssänkningen per kategori
          </span>
        </h2>
        <table className="data-table">
          <thead>
            <tr>
              <th>Kategori</th>
              <th style={{ textAlign: "right" }}>Produkter</th>
              <th style={{ textAlign: "right" }}>Genomslag</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((cat) => (
              <tr key={cat.categoryId}>
                <td>{cat.category}</td>
                <td className="number">{cat.found}</td>
                <td
                  className="number"
                  style={{
                    color:
                      (cat.passThroughPercent ?? 0) >= 80
                        ? "var(--color-green)"
                        : (cat.passThroughPercent ?? 0) >= 40
                          ? "var(--color-yellow)"
                          : "var(--color-red)",
                  }}
                >
                  {cat.passThroughPercent != null
                    ? `${cat.passThroughPercent.toFixed(0)}%`
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  // Pre-cut: show all categories with status indicators
  return (
    <div className="card" id="kategori">
      <h2>
        Bevakade kategorier
        <span className="subtitle">
          31 livsmedelskategorier bevakas. Från 1 april visas genomslaget per kategori.
        </span>
      </h2>
      <div className="category-grid">
        {ALL_CATEGORIES.map((name) => {
          const cat = catMap.get(name);
          const hasData = cat && cat.found > 0;
          return (
            <div
              key={name}
              className={`category-chip ${hasData ? "active" : ""}`}
            >
              {name}
              {hasData && <span className="category-count">{cat.found}</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
