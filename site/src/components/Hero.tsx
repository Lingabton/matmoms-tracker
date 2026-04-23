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
        Jämför <em>matpriser</em> i hela Sverige
      </h1>
      <p className="lead">
        Sök bland {summary.totalProducts} varor, bygg din varukorg och se vilken kedja
        som är billigast. Priserna uppdateras varje morgon
        från {summary.totalStores} butiker i 9 städer.
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
      <div className="hero-actions">
        <a href="#sok" className="hero-btn primary">Sök produkter</a>
        <a href="#priser" className="hero-btn secondary">Se priser</a>
      </div>
    </header>
  );
}
