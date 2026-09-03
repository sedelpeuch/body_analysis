import type { TimeseriesPointOut } from "../types";

export function mergeTimeseries(series: Record<string, TimeseriesPointOut[]>): Record<string, unknown>[] {
  const dates = new Set<string>();
  for (const points of Object.values(series)) {
    for (const point of points) dates.add(point.at);
  }
  const sortedDates = Array.from(dates).sort();
  const metrics = Object.keys(series);
  const byMetricByDate = new Map(
    metrics.map((metric) => [metric, new Map(series[metric].map((p) => [p.at, p.value]))]),
  );

  return sortedDates.map((at) => {
    const row: Record<string, unknown> = { at };
    for (const metric of metrics) {
      row[metric] = byMetricByDate.get(metric)!.get(at) ?? null;
    }
    return row;
  });
}
