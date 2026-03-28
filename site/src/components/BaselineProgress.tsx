import type { SiteData } from "../hooks/useData";

interface Props {
  data: SiteData;
}

export function BaselineProgress({ data }: Props) {
  const { baseline, summary } = data;
  const daysTarget = 7;
  const daysCollected = summary.daysOfData;
  const daysLeft = Math.max(0, daysTarget - daysCollected);

  return (
    <div className="card">
      <h2>
        Baslinjeinsamling
        <span className="subtitle">
          Prisnivalinjen fore momssankningen &mdash; ju fler dagar, desto sakrare
          resultat
        </span>
      </h2>
      <div className="stat-grid">
        <div className="stat">
          <div className="value">{daysCollected}</div>
          <div className="label">Dagar insamlat</div>
        </div>
        <div className="stat">
          <div className="value">{daysLeft}</div>
          <div className="label">Dagar kvar</div>
        </div>
        <div className="stat">
          <div className="value">
            {summary.foundObservations.toLocaleString("sv-SE")}
          </div>
          <div className="label">Prisobservationer</div>
        </div>
        <div className="stat">
          <div className="value">{baseline.coveragePercent}%</div>
          <div className="label">Tackning</div>
        </div>
      </div>

      {baseline.daily.length > 0 && (
        <div style={{ marginTop: "1.5rem" }}>
          <h2 style={{ fontSize: "0.9rem", marginBottom: "0.5rem" }}>
            Observationer per dag
          </h2>
          <div
            style={{
              display: "flex",
              gap: "4px",
              alignItems: "flex-end",
              height: "60px",
            }}
          >
            {baseline.daily.map((d) => {
              const maxFound = Math.max(...baseline.daily.map((x) => x.found));
              const height = maxFound > 0 ? (d.found / maxFound) * 100 : 0;
              return (
                <div
                  key={d.date}
                  style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center" }}
                >
                  <div
                    style={{
                      width: "100%",
                      maxWidth: "40px",
                      height: `${height}%`,
                      minHeight: "2px",
                      background: "var(--color-accent)",
                      borderRadius: "3px 3px 0 0",
                    }}
                  />
                  <span style={{ fontSize: "0.65rem", color: "var(--color-text-secondary)", marginTop: "4px" }}>
                    {d.date.slice(5)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
