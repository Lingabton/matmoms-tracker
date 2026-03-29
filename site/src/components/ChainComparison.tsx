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

  // Pre-cut: show chain overview with store counts and avg prices
  return (
    <div className="card" id="kedja">
      <h2>
        Bevakade kedjor
        <span className="subtitle">
          Från 1 april visas hur stor del av momssänkningen varje kedja
          för vidare till konsumenterna
        </span>
      </h2>
      {byChain.map((chain) => (
        <div className="chain-bar" key={chain.chain}>
          <span className="chain-name" style={{ width: "80px" }}>{chain.chainName}</span>
          <div className="bar-container">
            <div
              className="bar-fill"
              style={{
                width: "0%",
                background: CHAIN_COLORS[chain.chain] ?? "var(--color-accent)",
                opacity: 0.3,
              }}
            />
            <span className="bar-pending">Väntar på momssänkningen...</span>
          </div>
          <span className="bar-value" style={{ color: "var(--color-text-secondary)" }}>
            {chain.stores} {chain.stores === 1 ? "butik" : "butiker"}
          </span>
        </div>
      ))}
    </div>
  );
}
