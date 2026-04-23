import type { CatalogProduct } from "../hooks/useCatalog";

interface Props {
  catalog: CatalogProduct[] | null;
}

const CHAINS = ["ica", "coop", "willys"] as const;
const CHAIN_LABELS: Record<string, string> = { ica: "ICA", coop: "Coop", willys: "Willys" };
const CHAIN_COLORS: Record<string, string> = {
  ica: "var(--ica)", coop: "var(--coop)", willys: "var(--willys)",
};

export function ChainComparison({ catalog }: Props) {
  // Count how many products each chain wins (cheapest price)
  const wins: Record<string, number> = { ica: 0, coop: 0, willys: 0 };
  const totals: Record<string, { sum: number; count: number }> = {
    ica: { sum: 0, count: 0 },
    coop: { sum: 0, count: 0 },
    willys: { sum: 0, count: 0 },
  };

  if (catalog) {
    for (const p of catalog) {
      const prices: { chain: string; price: number }[] = [];
      for (const c of CHAINS) {
        const price = p.prices[c];
        if (price != null) prices.push({ chain: c, price });
      }

      for (const { chain, price } of prices) {
        totals[chain].sum += price;
        totals[chain].count += 1;
      }

      if (prices.length > 1) {
        const cheapest = prices.reduce((a, b) => (a.price < b.price ? a : b));
        wins[cheapest.chain]++;
      }
    }
  }

  const totalProducts = catalog
    ? catalog.filter((p) => {
        const n = CHAINS.filter((c) => p.prices[c] != null).length;
        return n > 1;
      }).length
    : 0;

  const maxWins = Math.max(...Object.values(wins), 1);

  return (
    <div className="section-block reveal" id="kedja">
      <div className="section-header">
        <h2>Vilken kedja är billigast?</h2>
        <p>
          Antal produkter där varje kedja har lägst pris
          {totalProducts > 0 && <> (av {totalProducts} jämförbara)</>}.
        </p>
      </div>

      {CHAINS.map((chain) => {
        const w = Math.max(3, (wins[chain] / maxWins) * 100);
        const avg = totals[chain].count > 0
          ? (totals[chain].sum / totals[chain].count).toFixed(0)
          : "—";

        return (
          <div className="chain-row" key={chain}>
            <div className="chain-name">{CHAIN_LABELS[chain]}</div>
            <div className="chain-track">
              <div
                className="chain-fill"
                style={{ width: `${w}%`, background: CHAIN_COLORS[chain] }}
              >
                {wins[chain] > 10 && wins[chain]}
              </div>
            </div>
            <div className="chain-value">
              <span>{wins[chain]} billigast</span>
              <span style={{ fontSize: "0.7rem", color: "var(--text-muted)", display: "block" }}>
                snitt {avg} kr
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
