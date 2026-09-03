import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { seriesColor } from "../../lib/chart-palette";

export interface SeriesSpec {
  key: string;
  label: string;
}

export interface LineSeriesCardProps {
  data: Record<string, unknown>[];
  series: SeriesSpec[];
  xKey: string;
  height?: number;
}

export function LineSeriesCard({ data, series, xKey, height = 240 }: LineSeriesCardProps) {
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="var(--color-line)" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey={xKey}
            stroke="var(--color-text-low)"
            tick={{ fill: "var(--color-text-mid)", fontSize: 12, fontFamily: "var(--font-mono)" }}
            tickLine={false}
            axisLine={{ stroke: "var(--color-line)" }}
          />
          <YAxis
            stroke="var(--color-text-low)"
            tick={{ fill: "var(--color-text-mid)", fontSize: 12, fontFamily: "var(--font-mono)" }}
            tickLine={false}
            axisLine={false}
            width={48}
          />
          <Tooltip
            contentStyle={{
              background: "var(--color-surface-raised)",
              border: "1px solid var(--color-line)",
              borderRadius: "var(--radius-card)",
              fontFamily: "var(--font-mono)",
              fontSize: 12,
            }}
            labelStyle={{ color: "var(--color-text-mid)" }}
          />
          {series.length > 1 && <Legend wrapperStyle={{ fontSize: 12, color: "var(--color-text-mid)" }} />}
          {series.map((s, index) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.label}
              stroke={seriesColor(index)}
              strokeWidth={2}
              dot={false}
              connectNulls={false}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
