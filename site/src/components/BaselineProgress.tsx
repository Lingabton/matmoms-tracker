import type { SiteData } from "../hooks/useData";

interface Props {
  data: SiteData;
}

export function BaselineProgress({ data }: Props) {
  const { baseline, summary } = data;
  const daysTarget = 7;
  const daysCollected = summary.daysOfData;
  const progressPercent = Math.min(100, (daysCollected / daysTarget) * 100);

  return (
    <div className="card">
      <h2>
        Baslinjeinsamling
        <span className="subtitle">
          Vi samlar in priser före momssänkningen för att kunna mäta
          förändringen. Ju fler dagar, desto säkrare resultat.
        </span>
      </h2>

      <div className="progress-bar-container">
        <div className="progress-bar-track">
          <div
            className="progress-bar-fill"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <div className="progress-bar-labels">
          <span>{daysCollected} av {daysTarget} dagar insamlade</span>
          <span>{summary.foundObservations.toLocaleString("sv-SE")} prisobservationer</span>
        </div>
      </div>

      <div className="stat-grid" style={{ marginTop: "1.25rem" }}>
        <div className="stat">
          <div className="value">{summary.totalProducts}</div>
          <div className="label">Produkter</div>
        </div>
        <div className="stat">
          <div className="value">{summary.totalStores}</div>
          <div className="label">Butiker</div>
        </div>
        <div className="stat">
          <div className="value">{summary.totalChains}</div>
          <div className="label">Kedjor</div>
        </div>
        <div className="stat">
          <div className="value">9</div>
          <div className="label">Städer</div>
        </div>
      </div>

      {baseline.daily.length > 1 && (
        <div style={{ marginTop: "1.5rem" }}>
          <h3 style={{ fontSize: "0.85rem", marginBottom: "0.5rem", fontWeight: 600 }}>
            Observationer per dag
          </h3>
          <div className="daily-bars">
            {baseline.daily.map((d) => {
              const maxFound = Math.max(...baseline.daily.map((x) => x.found));
              const height = maxFound > 0 ? (d.found / maxFound) * 100 : 0;
              return (
                <div key={d.date} className="daily-bar">
                  <div
                    className="daily-bar-fill"
                    style={{ height: `${height}%` }}
                  />
                  <span className="daily-bar-label">{d.date.slice(5)}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
