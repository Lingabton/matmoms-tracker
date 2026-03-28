import type { SiteData } from "../hooks/useData";

interface Props {
  data: SiteData;
}

export function CategoryTable({ data }: Props) {
  const { byCategory, isPostCut } = data;

  const sorted = [...byCategory].sort((a, b) => {
    if (isPostCut) {
      return (b.passThroughPercent ?? 0) - (a.passThroughPercent ?? 0);
    }
    return b.found - a.found;
  });

  return (
    <div className="card" id="kategori">
      <h2>
        Per produktkategori
        <span className="subtitle">
          {isPostCut
            ? "Genomslag av momssankningen per kategori"
            : "Antal prisobservationer per kategori i baslinjeperioden"}
        </span>
      </h2>
      <table className="data-table">
        <thead>
          <tr>
            <th>Kategori</th>
            <th style={{ textAlign: "right" }}>Produkter</th>
            {isPostCut ? (
              <th style={{ textAlign: "right" }}>Genomslag</th>
            ) : (
              <>
                <th style={{ textAlign: "right" }}>Snittpris</th>
                <th style={{ textAlign: "right" }}>Traffsaker</th>
              </>
            )}
          </tr>
        </thead>
        <tbody>
          {sorted.map((cat) => (
            <tr key={cat.categoryId}>
              <td>{cat.category}</td>
              <td className="number">{cat.found}</td>
              {isPostCut ? (
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
              ) : (
                <>
                  <td className="number">
                    {cat.avgPrice != null ? `${cat.avgPrice.toFixed(0)} kr` : "—"}
                  </td>
                  <td className="number">{cat.hitRate}%</td>
                </>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
