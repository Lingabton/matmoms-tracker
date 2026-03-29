import type { SiteData } from "../hooks/useData";

interface Props {
  data: SiteData;
}

const COLORS: Record<string, string> = {
  ica: "var(--ica)", coop: "var(--coop)", willys: "var(--willys)",
};

export function ChainComparison({ data }: Props) {
  const { byChain, isPostCut, expectedDropPercent } = data;

  const maxVal = isPostCut
    ? Math.max(...byChain.map((c) => Math.abs(c.passThroughPercent ?? 0)), 100)
    : Math.max(...byChain.map((c) => c.found), 1);

  return (
    <div className="section-block reveal" id="kedja">
      <div className="section-header">
        <h2>{isPostCut ? "Genomslag per kedja" : "Insamlad data per kedja"}</h2>
        <p>
          {isPostCut
            ? `Andel av ${expectedDropPercent}%-sänkningen som nått konsumenterna`
            : "Antal verifierade prisobservationer hittills i baslinjeperioden"}
        </p>
      </div>

      {byChain.map((chain) => {
        if (isPostCut) {
          const pt = chain.passThroughPercent ?? 0;
          const w = Math.max(3, (Math.abs(pt) / maxVal) * 100);
          return (
            <div className="chain-row" key={chain.chain}>
              <div className="chain-name">{chain.chainName}</div>
              <div className="chain-track">
                <div className="chain-fill" style={{ width: `${w}%`, background: COLORS[chain.chain] }} />
              </div>
              <div className="chain-value">{pt.toFixed(0)}%</div>
            </div>
          );
        }

        const w = Math.max(3, (chain.found / maxVal) * 100);
        return (
          <div className="chain-row" key={chain.chain}>
            <div className="chain-name">{chain.chainName}</div>
            <div className="chain-track">
              <div className="chain-fill" style={{ width: `${w}%`, background: COLORS[chain.chain] }}>
                {chain.found > 50 && chain.found}
              </div>
            </div>
            <div className="chain-value">{chain.found} priser</div>
          </div>
        );
      })}
    </div>
  );
}
