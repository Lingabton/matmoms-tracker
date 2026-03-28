import type { SiteData } from "../hooks/useData";

interface Props {
  data: SiteData;
}

const CHAIN_COLORS: Record<string, string> = {
  ica: "var(--color-ica)",
  coop: "var(--color-coop)",
  willys: "var(--color-willys)",
};

export function ChainComparison({ data }: Props) {
  const { byChain, isPostCut, expectedDropPercent } = data;

  if (isPostCut) {
    const maxPt = Math.max(
      ...byChain.map((c) => Math.abs(c.passThroughPercent ?? 0)),
      100
    );

    return (
      <div className="card" id="kedja">
        <h2>
          Genomslag per kedja
          <span className="subtitle">
            Andel av {expectedDropPercent}%-sankningen som natt konsumenterna
          </span>
        </h2>
        {byChain.map((chain) => {
          const pt = chain.passThroughPercent ?? 0;
          const width = Math.max(5, (Math.abs(pt) / maxPt) * 100);
          return (
            <div className="chain-bar" key={chain.chain}>
              <span className="chain-name">{chain.chainName}</span>
              <div className="bar-container">
                <div
                  className="bar-fill"
                  style={{
                    width: `${width}%`,
                    background: CHAIN_COLORS[chain.chain] ?? "var(--color-accent)",
                  }}
                />
              </div>
              <span className="bar-value">{pt.toFixed(0)}%</span>
            </div>
          );
        })}
      </div>
    );
  }

  // Pre-cut: show average prices as preview
  return (
    <div className="card" id="kedja">
      <h2>
        Prisdata per kedja
        <span className="subtitle">
          Genomsnittspris i baslinjeperioden (fore momssankningen)
        </span>
      </h2>
      {byChain.map((chain) => (
        <div className="chain-bar" key={chain.chain}>
          <span className="chain-name">{chain.chainName}</span>
          <div className="bar-container">
            <div
              className="bar-fill"
              style={{
                width: `${chain.hitRate}%`,
                background: CHAIN_COLORS[chain.chain] ?? "var(--color-accent)",
              }}
            >
              {chain.hitRate > 20 && `${chain.hitRate}%`}
            </div>
          </div>
          <span className="bar-value">
            {chain.avgPrice != null ? `${chain.avgPrice.toFixed(0)} kr` : "—"}
          </span>
        </div>
      ))}
      <p
        style={{
          fontSize: "0.8rem",
          color: "var(--color-text-secondary)",
          marginTop: "1rem",
        }}
      >
        Stapeln visar traffsaker (andel produkter med pris). Fran 1 april visas
        genomslaget av momssankningen.
      </p>
    </div>
  );
}
