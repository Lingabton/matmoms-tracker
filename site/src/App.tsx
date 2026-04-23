import { useEffect } from "react";
import { useData } from "./hooks/useData";
import { useCatalog } from "./hooks/useCatalog";
import { useBasket } from "./hooks/useBasket";
import { Nav } from "./components/Nav";
import { Hero } from "./components/Hero";
import { PricePreview } from "./components/PricePreview";
import { ProductSearch } from "./components/ProductSearch";
import { BasketBuilder } from "./components/BasketBuilder";
import { ChainComparison } from "./components/ChainComparison";
import { CategoryTable } from "./components/CategoryTable";
import { Methodology } from "./components/Methodology";
import { JournalistCTA } from "./components/JournalistCTA";
import { EmbedInfo } from "./components/EmbedInfo";
import { Timeline } from "./components/Timeline";

function App() {
  const { data, loading, error } = useData();
  const { catalog, load: loadCatalog } = useCatalog();
  const basket = useBasket();

  // Load catalog eagerly once main data is ready
  useEffect(() => {
    if (data) loadCatalog();
  }, [data]);

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "40vh 2rem 0", fontFamily: "var(--font-display)" }}>
        <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>Laddar data...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{ textAlign: "center", padding: "40vh 2rem 0", fontFamily: "var(--font-display)" }}>
        <p style={{ color: "var(--accent)" }}>Kunde inte ladda data: {error}</p>
      </div>
    );
  }

  const basketIds = new Set(basket.items.map((i) => i.productId));

  return (
    <>
      <Nav basketCount={basket.count} />
      <Hero data={data} />

      <div className="section">
        <PricePreview data={data} />

        {catalog && (
          <ProductSearch
            catalog={catalog}
            onAdd={(p) => basket.add({ id: p.id, name: p.name, brand: p.brand, prices: p.prices })}
            basketIds={basketIds}
          />
        )}

        {basket.items.length > 0 && (
          <BasketBuilder
            items={basket.items}
            totals={basket.totals()}
            onUpdateQty={basket.updateQty}
            onRemove={basket.remove}
            onClear={basket.clear}
          />
        )}

        <Timeline data={data} />
        <ChainComparison data={data} />
        <CategoryTable data={data} />
      </div>

      <div className="section">
        <EmbedInfo />
      </div>

      <JournalistCTA data={data} />

      <div className="section">
        <Methodology />
      </div>

      <footer>
        <div className="section">
          <p><strong>Matmoms</strong> &mdash; Daglig prisjämförelse av matpriser i Sverige</p>
          <p style={{ marginTop: "0.3rem" }}>
            Senast uppdaterad: {new Date(data.generatedAt).toLocaleDateString("sv-SE")}
          </p>
          <div className="footer-links">
            <a href="https://github.com/Lingabton/matmoms-tracker">GitHub</a>
            <span>&middot;</span>
            <a href="mailto:gabriel.linton@gmail.com">Kontakt</a>
          </div>
        </div>
      </footer>
    </>
  );
}

export default App;
