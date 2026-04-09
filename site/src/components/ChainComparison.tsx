import type { SiteData } from "../hooks/useData";

interface Props {
  data: SiteData;
}

const COLORS: Record<string, string> = {
  ica: "var(--ica)", coop: "var(--coop)", willys: "var(--willys)",
};

export function ChainComparison({ data }: Props) {
  const { byChain, isPostCut } = data;

  const maxVal = isPostCut
    ? Math.max(...byChain.map((c) => Math.abs(c.passThroughPercent ?? 0)), 100)
    : Math.max(...byChain.map((c) => c.found), 1);

  return (
    <div className="section-block reveal" id="kedja">
      <div className="section-header">
        <h2>Data per kedja</h2>
        <p>
          {isPostCut
            ? "Antal prisobservationer och momssänkningens genomslag (ICA verifierad)"
            : "Antal verifierade prisobservationer hittills"}
        </p>
      </div>

      {byChain.map((chain) => {
        if (isPostCut) {
          const pt = chain.passThroughPercent ?? 0;
          const w = Math.max(3, (Math.abs(pt) / maxVal) * 100);
          const unverified = chain.verified === false;
          return (
            <div className="chain-row" key={chain.chain} style={unverified ? { opacity: 0.45 } : {}}>
              <div className="chain-name">
                {chain.chainName}
                {unverified && <span style={{ fontSize: "0.6rem", display: "block", color: "var(--text-muted)" }}>verifieras</span>}
              </div>
              <div className="chain-track">
                <div className="chain-fill" style={{
                  width: `${w}%`,
                  background: unverified ? "var(--text-muted)" : COLORS[chain.chain],
                }} />
              </div>
              <div className="chain-value" style={unverified ? { color: "var(--text-muted)" } : {}}>
                {unverified ? "—" : `${pt.toFixed(0)}%`}
              </div>
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
