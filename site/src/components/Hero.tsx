import type { SiteData } from "../hooks/useData";

interface Props {
  data: SiteData;
}

export function Hero({ data }: Props) {
  const { summary } = data;

  return (
    <header className="hero">
      <div className="overline">Daglig prisbevakning &mdash; ICA, Coop, Willys</div>
      <h1>
        Var är maten <em>billigast</em>?
      </h1>
      <p className="lead">
        Vi jämför matpriser dagligen hos Sveriges tre största kedjor.{" "}
        {summary.totalProducts} varor i {summary.totalStores} butiker
        över 9 städer. Data uppdateras varje morgon.
      </p>
      <div className="hero-stats">
        <div className="hero-stat">
          <span className="hero-stat-number">
            {summary.foundObservations.toLocaleString("sv-SE")}
          </span>
          <span className="hero-stat-label">prisobservationer</span>
        </div>
        <div className="hero-stat">
          <span className="hero-stat-number">{summary.daysOfData}</span>
          <span className="hero-stat-label">dagar data</span>
        </div>
        <div className="hero-stat">
          <span className="hero-stat-number">3</span>
          <span className="hero-stat-label">kedjor</span>
        </div>
      </div>
    </header>
  );
}
