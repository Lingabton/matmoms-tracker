import { useState, useMemo } from "react";
import type { CatalogProduct } from "../hooks/useCatalog";
import { ProductTrend } from "./ProductTrend";

interface Props {
  catalog: CatalogProduct[];
  onAdd: (product: CatalogProduct) => void;
  basketIds: Set<number>;
}

const CHAINS = ["ica", "coop", "willys"] as const;
const CHAIN_LABELS: Record<string, string> = { ica: "ICA", coop: "Coop", willys: "Willys" };

export function ProductSearch({ catalog, onAdd, basketIds }: Props) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const categories = useMemo(() => {
    const cats = [...new Set(catalog.map((p) => p.category))].sort();
    return cats;
  }, [catalog]);

  const filtered = useMemo(() => {
    const q = query.toLowerCase().trim();
    return catalog
      .filter((p) => {
        if (category && p.category !== category) return false;
        if (!q) return true;
        return (
          p.name.toLowerCase().includes(q) ||
          p.brand.toLowerCase().includes(q)
        );
      })
      .slice(0, 50);
  }, [catalog, query, category]);

  return (
    <div className="section-block reveal" id="sok">
      <div className="section-header">
        <h2>Sök &amp; jämför</h2>
        <p>Hitta en vara och se priser hos alla kedjor. Klicka for prishistorik.</p>
      </div>

      <div className="search-controls">
        <input
          type="text"
          className="search-input"
          placeholder="Sök produkt, t.ex. mjölk, pasta, ägg..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select
          className="search-select"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        >
          <option value="">Alla kategorier</option>
          {categories.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      {(query || category) && (
        <div className="search-results">
          <div className="search-count">
            {filtered.length}{filtered.length === 50 ? "+" : ""} produkter
          </div>
          {filtered.map((product) => {
            const prices = CHAINS.map((c) => product.prices[c] ?? null);
            const valid = prices.filter((p): p is number => p !== null);
            const min = valid.length > 1 ? Math.min(...valid) : null;
            const isExpanded = expandedId === product.id;
            const inBasket = basketIds.has(product.id);

            return (
              <div key={product.id} className="search-item">
                <div
                  className="search-item-main"
                  onClick={() => setExpandedId(isExpanded ? null : product.id)}
                >
                  <div className="search-item-info">
                    <span className="search-item-name">{product.name}</span>
                    <span className="search-item-brand">{product.brand}</span>
                  </div>
                  <div className="search-item-prices">
                    {CHAINS.map((c) => {
                      const price = product.prices[c];
                      if (price == null) return (
                        <span key={c} className="search-price missing">
                          <span className="search-price-chain">{CHAIN_LABELS[c]}</span>
                          &mdash;
                        </span>
                      );
                      const isCheapest = price === min;
                      return (
                        <span key={c} className={`search-price ${isCheapest ? "cheapest" : ""}`}>
                          <span className="search-price-chain">{CHAIN_LABELS[c]}</span>
                          {price.toFixed(2)} kr
                        </span>
                      );
                    })}
                  </div>
                  <button
                    className={`add-btn ${inBasket ? "in-basket" : ""}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      onAdd(product);
                    }}
                    title={inBasket ? "Lägg till fler" : "Lägg i varukorg"}
                  >
                    {inBasket ? "+" : "+"}
                  </button>
                </div>
                {isExpanded && product.history.length > 1 && (
                  <ProductTrend product={product} />
                )}
              </div>
            );
          })}
          {filtered.length === 0 && (
            <div className="search-empty">Inga produkter hittades</div>
          )}
        </div>
      )}

      {!query && !category && (
        <div className="search-hint">
          Skriv i sökfältet eller välj en kategori för att börja jämföra priser.
        </div>
      )}
    </div>
  );
}
