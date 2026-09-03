import { EmptyValue } from "../empty-state/EmptyValue";

export interface StatTileProps {
  label: string;
  value: number | string | null;
  unit?: string;
}

export function StatTile({ label, value, unit }: StatTileProps) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs text-text-mid">{label}</span>
      <span className="tabular text-xl text-text-high">
        {value === null ? <EmptyValue /> : value}
        {value !== null && unit ? <span className="ml-1 text-sm text-text-mid">{unit}</span> : null}
      </span>
    </div>
  );
}
