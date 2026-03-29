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
            Andel av {expectedDropPercent}%-sänkningen som nått konsumenterna
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

  // Pre-cut: show observations and stores per chain
  const maxObs = Math.max(...byChain.map((c) => c.found), 1);

  return (
    <div className="card" id="kedja">
      <h2>
        Insamlad data per kedja
        <span className="subtitle">
          Antal insamlade prisobservationer hittills i baslinjeperioden
        </span>
      </h2>
      {byChain.map((chain) => {
        const width = Math.max(5, (chain.found / maxObs) * 100);
        return (
          <div className="chain-bar" key={chain.chain}>
            <span className="chain-name" style={{ width: "80px" }}>{chain.chainName}</span>
            <div className="bar-container">
              <div
                className="bar-fill"
                style={{
                  width: `${width}%`,
                  background: CHAIN_COLORS[chain.chain] ?? "var(--color-accent)",
                }}
              >
                {chain.found > 20 && chain.found}
              </div>
            </div>
            <span className="bar-value">
              {chain.found} priser
            </span>
          </div>
        );
      })}
      <p className="card-footnote">
        Stapeln visar antal prisobservationer. Från 1 april visas genomslaget av momssänkningen per kedja.
      </p>
    </div>
  );
}
