import { useData } from "./hooks/useData";
import { Nav } from "./components/Nav";
import { Hero } from "./components/Hero";
import { BaselineProgress } from "./components/BaselineProgress";
import { ChainComparison } from "./components/ChainComparison";
import { CategoryTable } from "./components/CategoryTable";
import { Methodology } from "./components/Methodology";
import { JournalistCTA } from "./components/JournalistCTA";

function App() {
  const { data, loading, error } = useData();

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
      <main className="container">
        <Hero data={data} />

        {!data.isPostCut && <BaselineProgress data={data} />}

        <ChainComparison data={data} />
        <CategoryTable data={data} />
        <JournalistCTA data={data} />
        <Methodology />
      </main>
      <footer>
        <div className="container">
          <p>
            matmoms.se &mdash; Oberoende bevakning av matmomssankningen 2026.
          </p>
          <p style={{ marginTop: "0.25rem" }}>
            Data uppdateras dagligen. Senast uppdaterad:{" "}
            {new Date(data.generatedAt).toLocaleDateString("sv-SE")}.
          </p>
        </div>
      </footer>
    </>
  );
}

export default App;
