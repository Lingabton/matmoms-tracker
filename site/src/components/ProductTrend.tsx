import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import type { CatalogProduct } from "../hooks/useCatalog";

interface Props {
  product: CatalogProduct;
}

const CHAIN_COLORS: Record<string, string> = {
  ica: "#e13205",
  coop: "#00aa46",
  willys: "#e30613",
};

const CHAIN_LABELS: Record<string, string> = { ica: "ICA", coop: "Coop", willys: "Willys" };
const CHAINS = ["ica", "coop", "willys"] as const;

export function ProductTrend({ product }: Props) {
  const { history } = product;
  if (history.length < 2) return null;

  const chains = CHAINS.filter((c) =>
    history.some((h) => (h as Record<string, unknown>)[c] != null)
  );

  return (
    <div className="trend-panel">
      <div className="trend-header">
        Prishistorik: {product.name}
      </div>
      <div style={{ width: "100%", height: 200 }}>
        <ResponsiveContainer>
          <LineChart data={history} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(10,22,40,0.06)" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10, fontFamily: "Space Mono" }}
              tickFormatter={(v: string) => v.slice(5)}
              stroke="rgba(10,22,40,0.2)"
            />
            <YAxis
              tick={{ fontSize: 10, fontFamily: "Space Mono" }}
              stroke="rgba(10,22,40,0.2)"
              tickFormatter={(v: number) => `${v.toFixed(0)}`}
              width={40}
              domain={["auto", "auto"]}
            />
            <Tooltip
              contentStyle={{
                fontFamily: "Space Grotesk",
                fontSize: "0.75rem",
                borderRadius: "6px",
                border: "1px solid #e8e6e1",
              }}
              formatter={(value: unknown, name: unknown) => [
                `${Number(value).toFixed(2)} kr`,
                CHAIN_LABELS[String(name)] || String(name),
              ] as [string, string]}
              labelFormatter={(label: unknown) => `${label}`}
            />
            {chains.map((chain) => (
              <Line
                key={chain}
                type="monotone"
                dataKey={chain}
                stroke={CHAIN_COLORS[chain]}
                strokeWidth={2}
                dot={{ r: 2 }}
                activeDot={{ r: 4 }}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="trend-legend">
        {chains.map((chain) => (
          <div key={chain} className="trend-legend-item">
            <div className="trend-legend-dot" style={{ background: CHAIN_COLORS[chain] }} />
            <span>{CHAIN_LABELS[chain]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
