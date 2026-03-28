import type { SiteData } from "../hooks/useData";

interface Props {
  data: SiteData;
}

export function Hero({ data }: Props) {
  const { summary, isPostCut, expectedDropPercent } = data;

  if (isPostCut && summary.passThroughPercent != null) {
    const pt = summary.passThroughPercent;
    const colorClass = pt >= 80 ? "positive" : pt >= 40 ? "neutral" : "negative";
    return (
      <div className="hero">
        <h1>
          Momssankningen pa mat &mdash;
          <br />
          hur mycket billigare blev det?
        </h1>
        <div className={`big-number ${colorClass}`}>{pt.toFixed(0)}%</div>
        <p className="lead">
          av den forvantade prissankningen pa {expectedDropPercent}% har natt
          konsumenterna. Baserat pa {summary.foundObservations.toLocaleString("sv-SE")}{" "}
          prisobservationer fran {summary.totalStores} butiker.
        </p>
      </div>
    );
  }

  return (
    <div className="hero">
      <h1>
        Matmomsen sanks fran 12% till 6%
        <br />
        den 1 april 2026
      </h1>
      <p className="lead">
        Vi bevakar {summary.totalProducts} matvaror i {summary.totalStores}{" "}
        butiker fran {summary.totalChains} kedjor for att mata om prissankningen
        nar konsumenterna. Priserna <em>borde</em> sjunka med{" "}
        {expectedDropPercent}%.
      </p>
      <div style={{ marginTop: "1.5rem" }}>
        <span className="badge baseline">Baslinjedata samlas in</span>
      </div>
    </div>
  );
}
