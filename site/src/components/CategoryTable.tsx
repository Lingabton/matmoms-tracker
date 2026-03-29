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
      <div className="section-block reveal" id="kategori">
        <div className="section-header">
          <h2>Per produktkategori</h2>
          <p>Genomslag av momssänkningen per kategori</p>
        </div>
        <table className="price-table">
          <thead>
            <tr>
              <th>Kategori</th>
              <th className="right">Produkter</th>
              <th className="right">Genomslag</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((cat) => (
              <tr key={cat.categoryId}>
                <td>{cat.category}</td>
                <td className="price-cell">{cat.found}</td>
                <td className="price-cell" style={{
                  color: (cat.passThroughPercent ?? 0) >= 80 ? "var(--green)"
                    : (cat.passThroughPercent ?? 0) >= 40 ? "var(--blue)" : "var(--accent)"
                }}>
                  {cat.passThroughPercent != null ? `${cat.passThroughPercent.toFixed(0)}%` : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  const withData = byCategory.filter((c) => c.found > 0);
  const withoutCount = byCategory.filter((c) => c.found === 0).length;

  if (withData.length === 0) return null;

  return (
    <div className="section-block reveal" id="kategori">
      <div className="section-header">
        <h2>Bevakade kategorier</h2>
        <p>Kategorier med insamlad prisdata. Från 1 april visas genomslaget.</p>
      </div>
      <div className="chip-grid">
        {withData
          .sort((a, b) => b.found - a.found)
          .map((cat) => (
            <div key={cat.categoryId} className="chip active">
              {cat.category}
              <span className="count">{cat.found}</span>
            </div>
          ))}
        {withoutCount > 0 && (
          <div className="chip">+{withoutCount} väntar på data</div>
        )}
      </div>
    </div>
  );
}
