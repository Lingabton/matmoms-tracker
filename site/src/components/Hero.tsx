import type { SiteData } from "../hooks/useData";

interface Props {
  data: SiteData;
}

function daysUntil(dateStr: string): number {
  const target = new Date(dateStr + "T00:00:00");
  const now = new Date();
  return Math.max(0, Math.ceil((target.getTime() - now.getTime()) / 86400000));
}

export function Hero({ data }: Props) {
  const { summary, isPostCut, expectedDropPercent, vatCutDate } = data;

  if (isPostCut && summary.passThroughPercent != null) {
    const pt = summary.passThroughPercent;
    const colorClass = pt >= 80 ? "positive" : pt >= 40 ? "neutral" : "negative";
    return (
      <header className="hero">
        <div className="overline">Matmomssänkningen 2026 &mdash; ICA</div>
        <h1>
          ICA sänkte priserna med <em>{(pt * expectedDropPercent / 100).toFixed(1)}%</em>
        </h1>
        <div className={`big-number ${colorClass}`}>{pt.toFixed(0)}%</div>
        <p className="lead">
          av den förväntade prissänkningen på {expectedDropPercent}% har
          nått konsumenterna hos ICA. Coop och Willys data under
          verifiering.
        </p>
      </header>
    );
  }

  const daysLeft = daysUntil(vatCutDate);

  return (
    <header className="hero">
      <div className="overline">Oberoende prisbevakning</div>
      <h1>
        Blir maten <em>verkligen</em> billigare?
      </h1>
      <p className="lead">
        Den 1 april sänks matmomsen från 12% till 6%. Priserna borde sjunka
        med {expectedDropPercent}% &mdash; men gör de det? Vi mäter dagligen{" "}
        {summary.totalProducts} varor i {summary.totalStores} butiker för att
        ta reda på det.
      </p>
      {daysLeft > 0 && (
        <div className="countdown-row">
          <div className="countdown-number">{daysLeft}</div>
          <div className="countdown-label">
            {daysLeft === 1 ? "dag" : "dagar"} till momssänkningen
          </div>
        </div>
      )}
    </header>
  );
}
