import type { SiteData } from "../hooks/useData";

interface Props {
  data: SiteData;
}

function daysUntil(dateStr: string): number {
  const target = new Date(dateStr + "T00:00:00");
  const now = new Date();
  const diff = target.getTime() - now.getTime();
  return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
}

export function Hero({ data }: Props) {
  const { summary, isPostCut, expectedDropPercent, vatCutDate } = data;

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

  const daysLeft = daysUntil(vatCutDate);

  return (
    <header className="hero" role="banner">
      <h1>
        Matmomsen sänks från 12% till 6%
        <br />
        den 1 april 2026
      </h1>
      <p className="lead">
        Priserna <em>borde</em> sjunka med {expectedDropPercent}% &mdash; men gör
        de det? Vi mäter dagligen {summary.totalProducts} matvaror i{" "}
        {summary.totalStores} butiker från ICA, Coop och Willys för att ta reda
        på det.
      </p>
      {daysLeft > 0 ? (
        <div className="countdown">
          <div className="countdown-number">{daysLeft}</div>
          <div className="countdown-label">
            {daysLeft === 1 ? "dag" : "dagar"} kvar till momssänkningen
          </div>
        </div>
      ) : (
        <div style={{ marginTop: "1.5rem" }}>
          <span className="badge live">Momssänkningen är här</span>
        </div>
      )}
    </header>
  );
}
