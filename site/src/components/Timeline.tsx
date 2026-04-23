import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import type { SiteData } from "../hooks/useData";

interface Props {
  data: SiteData;
}

const CHAIN_COLORS: Record<string, string> = {
  ica: "#e13205",
  coop: "#00aa46",
  willys: "#e30613",
};

export function Timeline({ data }: Props) {
  const { timeline, vatCutDate } = data;
  if (!timeline || timeline.length === 0) return null;

  // Pivot: one row per date with chain prices as columns
  const byDate = new Map<string, Record<string, number | null>>();
  for (const t of timeline) {
    if (!byDate.has(t.date)) {
      byDate.set(t.date, { date: t.date } as any);
    }
    const row = byDate.get(t.date)!;
    (row as any)[t.chain] = t.avgPrice;
  }

  const chartData = Array.from(byDate.values()).sort((a: any, b: any) =>
    a.date.localeCompare(b.date)
  );

  if (chartData.length < 2) return null;

  const chains = [...new Set(timeline.map((t) => t.chain))];

  return (
    <div className="section-block reveal" id="tidslinje">
      <div className="section-header">
        <h2>Prisutveckling</h2>
        <p>Genomsnittspris per kedja och dag. Streckad linje = momssänkning 1 april (12% &rarr; 6%).</p>
      </div>
      <div style={{ width: "100%", height: 300 }}>
        <ResponsiveContainer>
          <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(10,22,40,0.06)" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11, fontFamily: "Space Mono" }}
              tickFormatter={(v: string) => v.slice(5)}
              stroke="rgba(10,22,40,0.2)"
            />
            <YAxis
              tick={{ fontSize: 11, fontFamily: "Space Mono" }}
              stroke="rgba(10,22,40,0.2)"
              tickFormatter={(v: number) => `${v.toFixed(0)} kr`}
              width={55}
            />
            <Tooltip
              contentStyle={{
                fontFamily: "Space Grotesk",
                fontSize: "0.8rem",
                borderRadius: "6px",
                border: "1px solid #e8e6e1",
              }}
              formatter={(value: any, name: any) => [
                `${Number(value).toFixed(2)} kr`,
                ({ ica: "ICA", coop: "Coop", willys: "Willys" } as any)[name] || name,
              ]}
              labelFormatter={(label: any) => `Datum: ${label}`}
            />
            <ReferenceLine
              x={vatCutDate}
              stroke="#ff4d4d"
              strokeDasharray="6 4"
              strokeWidth={2}
              label={{
                value: "1 april",
                position: "top",
                style: { fontSize: 11, fontFamily: "Space Mono", fill: "#ff4d4d" },
              }}
            />
            {chains.map((chain) => (
              <Line
                key={chain}
                type="monotone"
                dataKey={chain}
                stroke={CHAIN_COLORS[chain] || "#999"}
                strokeWidth={2.5}
                dot={{ r: 3 }}
                activeDot={{ r: 5 }}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div style={{ display: "flex", gap: "1.5rem", justifyContent: "center", marginTop: "0.75rem" }}>
        {chains.map((chain) => (
          <div key={chain} style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <div style={{ width: 12, height: 3, borderRadius: 2, background: CHAIN_COLORS[chain] }} />
            <span style={{ fontFamily: "Space Grotesk", fontSize: "0.75rem", fontWeight: 600 }}>
              {{ ica: "ICA", coop: "Coop", willys: "Willys" }[chain]}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
