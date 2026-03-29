import type { SiteData } from "../hooks/useData";

interface Props {
  data: SiteData;
}

export function BaselineProgress({ data }: Props) {
  const { summary } = data;
  const daysTarget = 7;
  const daysCollected = summary.daysOfData;
  const progressPercent = Math.min(100, (daysCollected / daysTarget) * 100);

  return (
    <div className="section-block reveal">
      <div className="section-header">
        <h2>Baslinjeinsamling</h2>
        <p>
          Vi samlar priser före momssänkningen. Ju fler dagar, desto säkrare
          jämförelse efteråt.
        </p>
      </div>

      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${progressPercent}%` }} />
      </div>
      <div className="progress-meta">
        <span>{daysCollected} av {daysTarget} dagar</span>
        <span>{summary.foundObservations.toLocaleString("sv-SE")} prisobservationer</span>
      </div>

      <div className="stats-row">
        <div className="stat-item">
          <div className="number">{summary.totalProducts}</div>
          <div className="label">Produkter</div>
        </div>
        <div className="stat-item">
          <div className="number">{summary.totalStores}</div>
          <div className="label">Butiker</div>
        </div>
        <div className="stat-item">
          <div className="number">{summary.totalChains}</div>
          <div className="label">Kedjor</div>
        </div>
        <div className="stat-item">
          <div className="number">9</div>
          <div className="label">Städer</div>
        </div>
      </div>
    </div>
  );
}
