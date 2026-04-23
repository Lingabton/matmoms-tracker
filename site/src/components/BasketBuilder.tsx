import type { BasketItem } from "../hooks/useBasket";

interface Props {
  items: BasketItem[];
  totals: Record<string, number | null>;
  onUpdateQty: (productId: number, qty: number) => void;
  onRemove: (productId: number) => void;
  onClear: () => void;
}

const CHAINS = ["ica", "coop", "willys"] as const;
const CHAIN_LABELS: Record<string, string> = { ica: "ICA", coop: "Coop", willys: "Willys" };
const CHAIN_COLORS: Record<string, string> = { ica: "var(--ica)", coop: "var(--coop)", willys: "var(--willys)" };

export function BasketBuilder({ items, totals, onUpdateQty, onRemove, onClear }: Props) {
  if (items.length === 0) return null;

  const validTotals: { chain: string; total: number }[] = [];
  for (const c of CHAINS) {
    const t = totals[c];
    if (t != null) validTotals.push({ chain: c, total: t });
  }
  const cheapest = validTotals.length > 1
    ? validTotals.reduce((a, b) => (a.total < b.total ? a : b)).chain
    : null;

  const savings = cheapest && validTotals.length > 1
    ? Math.max(...validTotals.map((t) => t.total)) - Math.min(...validTotals.map((t) => t.total))
    : 0;

  return (
    <div className="section-block reveal" id="varukorg">
      <div className="section-header">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <h2>Din varukorg</h2>
          <button className="basket-clear" onClick={onClear}>Rensa</button>
        </div>
        <p>
          {items.length} vara{items.length !== 1 ? "r" : ""} &mdash; jämför
          totalkostnad mellan kedjorna
        </p>
      </div>

      <div className="basket-totals">
        {CHAINS.map((chain) => {
          const total = totals[chain];
          const isCheapest = chain === cheapest;
          return (
            <div
              key={chain}
              className={`basket-total-card ${isCheapest ? "cheapest" : ""}`}
              style={{ borderColor: isCheapest ? CHAIN_COLORS[chain] : undefined }}
            >
              <div className="basket-total-chain">{CHAIN_LABELS[chain]}</div>
              <div className="basket-total-price">
                {total != null ? `${total.toFixed(2)} kr` : "Saknar data"}
              </div>
              {isCheapest && savings > 0 && (
                <div className="basket-total-badge">
                  Billigast! Spara {savings.toFixed(0)} kr
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="basket-items">
        {items.map((item) => (
          <div key={item.productId} className="basket-item">
            <div className="basket-item-info">
              <span className="basket-item-name">{item.name}</span>
              <span className="basket-item-brand">{item.brand}</span>
            </div>
            <div className="basket-item-controls">
              <button
                className="qty-btn"
                onClick={() => onUpdateQty(item.productId, item.qty - 1)}
              >
                &minus;
              </button>
              <span className="qty-display">{item.qty}</span>
              <button
                className="qty-btn"
                onClick={() => onUpdateQty(item.productId, item.qty + 1)}
              >
                +
              </button>
              <button
                className="remove-btn"
                onClick={() => onRemove(item.productId)}
                title="Ta bort"
              >
                &times;
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
