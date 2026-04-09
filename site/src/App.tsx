import { useData } from "./hooks/useData";
import { Nav } from "./components/Nav";
import { Hero } from "./components/Hero";
import { PricePreview } from "./components/PricePreview";
import { ChainComparison } from "./components/ChainComparison";
import { CategoryTable } from "./components/CategoryTable";
import { Methodology } from "./components/Methodology";
import { JournalistCTA } from "./components/JournalistCTA";
import { EmbedInfo } from "./components/EmbedInfo";
import { Timeline } from "./components/Timeline";

function App() {
  const { data, loading, error } = useData();

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

  return (
    <>
      <Nav />
      <Hero data={data} />

      <div className="section">
        <PricePreview data={data} />
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
