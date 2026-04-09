import type { SiteData } from "../hooks/useData";

interface Props {
  data: SiteData;
}

const CHAIN_LABELS: Record<string, string> = { ica: "ICA", coop: "Coop", willys: "Willys" };
const CHAINS = ["ica", "coop", "willys"] as const;

export function PricePreview({ data }: Props) {
  const { pricePreview } = data;
  if (!pricePreview || pricePreview.length === 0) return null;

  return (
    <div className="section-block reveal" id="priser">
      <div className="section-header">
        <h2>Prisjämförelse</h2>
        <p>
          Aktuella priser på vanliga matvaror. Lägsta pris markerat i grönt.
          Uppdateras dagligen.
        </p>
      </div>
      <div style={{ overflowX: "auto" }}>
        <table className="price-table">
          <thead>
            <tr>
              <th>Produkt</th>
              {CHAINS.map((c) => (
                <th key={c} className="right">{CHAIN_LABELS[c]}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pricePreview.map((product) => {
              const prices = CHAINS.map((c) => product.prices[c] ?? null);
              const valid = prices.filter((p): p is number => p !== null);
              const min = Math.min(...valid);

              return (
                <tr key={product.name}>
                  <td className="product-name">{product.name}</td>
                  {CHAINS.map((c) => {
                    const price = product.prices[c];
                    if (price == null) {
                      return <td key={c} className="price-cell missing">&mdash;</td>;
                    }
                    const isCheapest = price === min && valid.length > 1;
                    return (
                      <td key={c} className={`price-cell ${isCheapest ? "cheapest" : ""}`}>
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
    </div>
  );
}
