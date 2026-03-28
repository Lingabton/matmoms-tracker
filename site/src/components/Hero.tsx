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
      <header className="hero" role="banner">
        <h1>
          Momssänkningen på mat &mdash;
          <br />
          hur mycket billigare blev det?
        </h1>
        <div className={`big-number ${colorClass}`} aria-label={`${pt.toFixed(0)} procent genomslag`}>
          {pt.toFixed(0)}%
        </div>
        <p className="lead">
          av den förväntade prissänkningen på {expectedDropPercent}% har nått
          konsumenterna. Baserat på {summary.foundObservations.toLocaleString("sv-SE")}{" "}
          prisobservationer från {summary.totalStores} butiker.
        </p>
      </header>
    );
  }

  return (
    <header className="hero" role="banner">
      <h1>
        Matmomsen sänks från 12% till 6%
        <br />
        den 1 april 2026
      </h1>
      <p className="lead">
        Vi bevakar {summary.totalProducts} matvaror i {summary.totalStores}{" "}
        butiker från {summary.totalChains} kedjor för att mäta om prissänkningen
        når konsumenterna. Priserna <em>borde</em> sjunka med{" "}
        {expectedDropPercent}%.
      </p>
      <div style={{ marginTop: "1.5rem" }}>
        <span className="badge baseline">Baslinjedata samlas in</span>
      </div>
    </header>
  );
}
