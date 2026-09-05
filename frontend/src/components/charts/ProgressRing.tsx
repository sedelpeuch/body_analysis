export interface ProgressRingProps {
  value: number;
  max: number;
  label: string;
  size?: number;
}

const STROKE_WIDTH = 8;

export function ProgressRing({ value, max, label, size = 96 }: ProgressRingProps) {
  const ratio = max > 0 ? Math.min(1, Math.max(0, value / max)) : 0;
  const radius = (size - STROKE_WIDTH) / 2;
  const circumference = 2 * Math.PI * radius;
  const gradientId = `progress-ring-gradient-${label.replace(/\s+/g, "-")}`;

  return (
    <div className="flex flex-col items-center gap-2">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <defs>
          <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--color-accent-green)" />
            <stop offset="100%" stopColor="var(--color-accent-blue)" />
          </linearGradient>
        </defs>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--color-line)"
          strokeWidth={STROKE_WIDTH}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={`url(#${gradientId})`}
          strokeWidth={STROKE_WIDTH}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - ratio)}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      <span className="tabular text-sm text-text-high">{Math.round(ratio * 100)}%</span>
      <span className="text-xs text-text-mid">{label}</span>
    </div>
  );
}
