export interface CalendarCell {
  day: string;
  value: number | null;
}

export interface CalendarHeatmapProps {
  cells: CalendarCell[];
  year: number;
}

function cellColor(value: number | null, max: number): string {
  if (value === null) return "var(--color-line)";
  if (max <= 0) return "var(--color-line)";
  const intensity = Math.min(1, Math.max(0, value / max));
  // Rampe séquentielle à teinte unique (vert), du plus sombre au plus clair —
  // jamais un arc-en-ciel, jamais une couleur de domaine détournée de son rôle.
  return `color-mix(in srgb, var(--color-accent-green) ${Math.round(10 + intensity * 90)}%, var(--color-surface))`;
}

export function CalendarHeatmap({ cells, year }: CalendarHeatmapProps) {
  const max = Math.max(0, ...cells.map((c) => c.value ?? 0));
  const startOfYear = new Date(year, 0, 1);
  const startWeekday = (startOfYear.getDay() + 6) % 7; // lundi = 0

  const byDay = new Map(cells.map((c) => [c.day, c.value]));
  const totalDays = ((Date.UTC(year + 1, 0, 1) - Date.UTC(year, 0, 1)) / 86_400_000);
  const columns = Math.ceil((totalDays + startWeekday) / 7);

  return (
    <div
      className="grid gap-1"
      style={{ gridTemplateColumns: `repeat(${columns}, 10px)`, gridTemplateRows: "repeat(7, 10px)", gridAutoFlow: "column" }}
    >
      {Array.from({ length: startWeekday }, (_, i) => (
        <div key={`pad-${i}`} />
      ))}
      {Array.from({ length: totalDays }, (_, i) => {
        const date = new Date(Date.UTC(year, 0, 1 + i));
        const iso = date.toISOString().slice(0, 10);
        const value = byDay.get(iso) ?? null;
        return (
          <div
            key={iso}
            title={`${iso} : ${value ?? "—"}`}
            className="rounded-[2px]"
            style={{ width: 10, height: 10, backgroundColor: cellColor(value, max) }}
          />
        );
      })}
    </div>
  );
}
