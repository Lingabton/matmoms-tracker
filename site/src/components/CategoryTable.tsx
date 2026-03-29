import type { SiteData } from "../hooks/useData";

interface Props {
  data: SiteData;
}

export function CategoryTable({ data }: Props) {
  const { byCategory, isPostCut } = data;

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

  // Pre-cut: show only categories with data
  const withData = byCategory.filter((c) => c.found > 0);
  const withoutData = byCategory.length > 0 ? byCategory.filter((c) => c.found === 0) : [];

  if (withData.length === 0) return null;

  return (
    <div className="card" id="kategori">
      <h2>
        Bevakade kategorier
        <span className="subtitle">
          Kategorier med insamlad prisdata. Från 1 april visas genomslaget per kategori.
        </span>
      </h2>
      <div className="category-grid">
        {withData
          .sort((a, b) => b.found - a.found)
          .map((cat) => (
            <div key={cat.categoryId} className="category-chip active">
              {cat.category}
              <span className="category-count">{cat.found}</span>
            </div>
          ))}
        {withoutData.length > 0 && (
          <div
            className="category-chip"
            style={{ fontStyle: "italic" }}
          >
            +{withoutData.length} kategorier väntar på data
          </div>
        )}
      </div>
    </div>
  );
}
