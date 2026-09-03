import { CartesianGrid, Legend, Line, LineChart, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { seriesColor } from "../../lib/chart-palette";
import { formatAxisTick } from "../../lib/format";
import type { PhaseBand } from "../../lib/phase-bands";

export interface SeriesSpec {
  key: string;
  label: string;
  // Fixe la couleur d'une métrique récurrente (poids, muscle, masse grasse...)
  // à travers les pages, plutôt que de la laisser dépendre de sa position
  // dans `series` — important depuis que chaque métrique a son propre
  // graphique à une seule série (index toujours 0 sinon).
  color?: string;
}

export interface LineSeriesCardProps {
  data: object[];
  series: SeriesSpec[];
  xKey: string;
  height?: number;
  phaseBands?: PhaseBand[];
}

export function LineSeriesCard({ data, series, xKey, height = 240, phaseBands = [] }: LineSeriesCardProps) {
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
            tickFormatter={formatAxisTick}
            minTickGap={32}
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
          {phaseBands.map((band) => (
            <ReferenceArea
              key={band.phaseId}
              x1={band.x1}
              x2={band.x2}
              fill={band.color}
              fillOpacity={0.12}
              stroke="none"
              ifOverflow="visible"
            />
          ))}
          {series.length > 1 && <Legend wrapperStyle={{ fontSize: 12, color: "var(--color-text-mid)" }} />}
          {series.map((s, index) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.label}
              stroke={s.color ?? seriesColor(index)}
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
