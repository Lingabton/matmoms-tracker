import type { CatalogProduct } from "../hooks/useCatalog";

interface Props {
  catalog: CatalogProduct[] | null;
}

const CHAINS = ["ica", "coop", "willys"] as const;
const CHAIN_LABELS: Record<string, string> = { ica: "ICA", coop: "Coop", willys: "Willys" };
const CHAIN_COLORS: Record<string, string> = {
  ica: "var(--ica)", coop: "var(--coop)", willys: "var(--willys)",
};

interface CatRow {
  category: string;
  avgs: Record<string, number | null>;
  cheapest: string | null;
  productCount: number;
}

export function CategoryTable({ catalog }: Props) {
  if (!catalog) return null;

  // Compute avg price per chain per category
  const byCat: Record<string, Record<string, { sum: number; n: number }>> = {};
  const catCounts: Record<string, number> = {};

  for (const p of catalog) {
    const cat = p.category;
    if (!byCat[cat]) {
      byCat[cat] = {};
      catCounts[cat] = 0;
    }
    catCounts[cat]++;
    for (const c of CHAINS) {
      const price = p.prices[c];
      if (price != null) {
        if (!byCat[cat][c]) byCat[cat][c] = { sum: 0, n: 0 };
        byCat[cat][c].sum += price;
        byCat[cat][c].n += 1;
      }
    }
  }

  const rows: CatRow[] = Object.entries(byCat).map(([cat, chains]) => {
    const avgs: Record<string, number | null> = {};
    for (const c of CHAINS) {
      const d = chains[c];
      avgs[c] = d && d.n > 0 ? Math.round(d.sum / d.n * 100) / 100 : null;
    }
    const valid = CHAINS.filter((c) => avgs[c] != null);
    const cheapest = valid.length > 1
      ? valid.reduce((a, b) => (avgs[a]! < avgs[b]! ? a : b))
      : null;
    return { category: cat, avgs, cheapest, productCount: catCounts[cat] };
  });

  rows.sort((a, b) => a.category.localeCompare(b.category, "sv"));

  return (
    <div className="section-block reveal" id="kategori">
      <div className="section-header">
        <h2>Billigast per kategori</h2>
        <p>Genomsnittligt pris per kedja och kategori. Lägst markerat.</p>
      </div>
      <div style={{ overflowX: "auto" }}>
        <table className="price-table">
          <thead>
            <tr>
              <th>Kategori</th>
              {CHAINS.map((c) => (
                <th key={c} className="right">{CHAIN_LABELS[c]}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.category}>
                <td className="product-name">
                  {row.category}
                  <span style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginLeft: "0.4rem" }}>
                    ({row.productCount})
                  </span>
                </td>
                {CHAINS.map((c) => {
                  const avg = row.avgs[c];
                  if (avg == null) {
                    return <td key={c} className="price-cell missing">&mdash;</td>;
                  }
                  const isCheapest = c === row.cheapest;
                  return (
                    <td
                      key={c}
                      className={`price-cell ${isCheapest ? "cheapest" : ""}`}
                      style={isCheapest ? { color: CHAIN_COLORS[c] } : undefined}
                    >
                      {avg.toFixed(0)} kr
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
