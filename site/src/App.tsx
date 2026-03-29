import { useEffect } from "react";
import { useData } from "./hooks/useData";
import { Nav } from "./components/Nav";
import { Hero } from "./components/Hero";
import { BaselineProgress } from "./components/BaselineProgress";
import { PricePreview } from "./components/PricePreview";
import { ChainComparison } from "./components/ChainComparison";
import { CategoryTable } from "./components/CategoryTable";
import { Methodology } from "./components/Methodology";
import { JournalistCTA } from "./components/JournalistCTA";

function App() {
  const { data, loading, error } = useData();

  // Smooth scroll for anchor links
  useEffect(() => {
    document.documentElement.style.scrollBehavior = "smooth";
  }, []);

  // Dynamic title update with live data
  useEffect(() => {
    if (!data) return;
    if (data.isPostCut && data.summary.passThroughPercent != null) {
      document.title = `${data.summary.passThroughPercent.toFixed(0)}% genomslag — Matmoms 2026: Blev maten billigare?`;
    }
  }, [data]);

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "4rem" }}>
        <p style={{ color: "var(--color-text-secondary)" }}>Laddar data...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{ textAlign: "center", padding: "4rem" }}>
        <p style={{ color: "var(--color-red)" }}>
          Kunde inte ladda data: {error}
        </p>
      </div>
    );
  }

  return (
    <>
      <Nav />
      <main className="container" role="main">
        <article>
          <Hero data={data} />

          {!data.isPostCut && (
            <section aria-label="Baslinjeinsamling">
              <BaselineProgress data={data} />
            </section>
          )}

          <section aria-label="Prisexempel">
            <PricePreview data={data} />
          </section>

          <section aria-label="Jämförelse per kedja">
            <ChainComparison data={data} />
          </section>

          <section aria-label="Per kategori">
            <CategoryTable data={data} />
          </section>
        </article>

        <aside aria-label="För journalister och forskare">
          <JournalistCTA data={data} />
        </aside>

        <section aria-label="Metod">
          <Methodology />
        </section>
      </main>
      <footer>
        <div className="container">
          <p>
            <strong>Matmoms</strong> — Oberoende bevakning av matmomssänkningen 2026
          </p>
          <p style={{ marginTop: "0.5rem" }}>
            Data uppdateras dagligen kl. 06:00. Senast uppdaterad:{" "}
            {new Date(data.generatedAt).toLocaleDateString("sv-SE")}.
          </p>
          <div className="footer-links">
            <a href="https://github.com/Lingabton/matmoms-tracker">GitHub</a>
            <span>·</span>
            <a href="mailto:gabriel.linton@gmail.com">Kontakt</a>
            <span>·</span>
            <span>Byggt med öppen data</span>
          </div>
        </div>
      </footer>
    </>
  );
}

export default App;
