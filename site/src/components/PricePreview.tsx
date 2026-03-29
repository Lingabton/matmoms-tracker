import type { SiteData } from "../hooks/useData";

interface Props {
  data: SiteData;
}

const CHAIN_LABELS: Record<string, string> = {
  ica: "ICA",
  coop: "Coop",
  willys: "Willys",
};

const CHAIN_COLORS: Record<string, string> = {
  ica: "var(--color-ica)",
  coop: "var(--color-coop)",
  willys: "var(--color-willys)",
};

export function PricePreview({ data }: Props) {
  const { pricePreview } = data;
  if (!pricePreview || pricePreview.length === 0) return null;

  const chains = ["ica", "coop", "willys"];

  return (
    <div className="card" id="priser">
      <h2>
        Prisexempel idag
        <span className="subtitle">
          Aktuella priser från våra bevakade butiker. Från 1 april jämförs dessa
          med baslinjen för att mäta genomslaget.
        </span>
      </h2>
      <div style={{ overflowX: "auto" }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Produkt</th>
              {chains.map((c) => (
                <th key={c} style={{ textAlign: "right", color: CHAIN_COLORS[c] }}>
                  {CHAIN_LABELS[c]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pricePreview.map((product) => {
              const prices = chains.map((c) => product.prices[c] ?? null);
              const validPrices = prices.filter((p): p is number => p !== null);
              const minPrice = Math.min(...validPrices);

              return (
                <tr key={product.name}>
                  <td>
                    <span style={{ fontWeight: 500 }}>{product.name}</span>
                  </td>
                  {chains.map((c) => {
                    const price = product.prices[c];
                    if (price == null) {
                      return (
                        <td key={c} className="number" style={{ color: "var(--color-border)" }}>
                          —
                        </td>
                      );
                    }
                    const isCheapest = price === minPrice && validPrices.length > 1;
                    return (
                      <td
                        key={c}
                        className="number"
                        style={{
                          fontWeight: isCheapest ? 700 : 400,
                          color: isCheapest ? "var(--color-green)" : undefined,
                        }}
                      >
                        {price.toFixed(2)} kr
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p
        style={{
          fontSize: "0.75rem",
          color: "var(--color-text-secondary)",
          marginTop: "0.75rem",
          fontStyle: "italic",
        }}
      >
        Lägsta pris markerat i grönt. Priser uppdateras dagligen. Kampanjpriser kan förekomma.
      </p>
    </div>
  );
}
