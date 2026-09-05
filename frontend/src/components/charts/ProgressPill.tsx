export interface ProgressPillProps {
  value: number;
  max?: number;
  color: string;
}

export function ProgressPill({ value, max = 1, color }: ProgressPillProps) {
  const ratio = max > 0 ? Math.min(1, Math.max(0, value / max)) : 0;
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-line">
      <div className="h-full rounded-full" style={{ width: `${ratio * 100}%`, backgroundColor: color }} />
    </div>
  );
}
