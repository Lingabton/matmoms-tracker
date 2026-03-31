import { useEffect, useRef } from "react";
import { useData } from "./hooks/useData";
import { Nav } from "./components/Nav";
import { Hero } from "./components/Hero";
import { BaselineProgress } from "./components/BaselineProgress";
import { PricePreview } from "./components/PricePreview";
import { ChainComparison } from "./components/ChainComparison";
import { CategoryTable } from "./components/CategoryTable";
import { Methodology } from "./components/Methodology";
import { JournalistCTA } from "./components/JournalistCTA";
import { NewsBanner } from "./components/NewsBanner";
import { EmbedInfo } from "./components/EmbedInfo";
import { Timeline } from "./components/Timeline";

function useScrollReveal() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
          }
        });
      },
      { threshold: 0.1, rootMargin: "0px 0px -40px 0px" }
    );

    const el = ref.current;
    if (el) {
      el.querySelectorAll(".reveal").forEach((node) => observer.observe(node));
    }

    return () => observer.disconnect();
  }, []);

  return ref;
}

function App() {
  const { data, loading, error } = useData();
  const contentRef = useScrollReveal();

  useEffect(() => {
    if (!data) return;
    if (data.isPostCut && data.summary.passThroughPercent != null) {
      document.title = `${data.summary.passThroughPercent.toFixed(0)}% genomslag — Matmoms 2026`;
    }
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

  return (
    <div ref={contentRef}>
      <Nav />

      <Hero data={data} />

      <div className="section">
        <NewsBanner />
        {!data.isPostCut && <BaselineProgress data={data} />}
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
          <p><strong>Matmoms</strong> &mdash; Oberoende bevakning av matmomssänkningen 2026</p>
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
    </div>
  );
}

export default App;
