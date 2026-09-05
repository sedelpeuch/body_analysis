import type { PhaseKind, PhaseOut } from "../api/types";

export interface PhaseBand {
  phaseId: number;
  label: string;
  x1: string;
  x2: string;
  color: string;
}

const KIND_COLOR: Record<PhaseKind, string> = {
  cut: "var(--color-accent-green)",
  bulk: "var(--color-accent-blue)",
  maintain: "var(--color-domain-phase)",
  free: "var(--color-text-low)",
};

// Aligne chaque bande sur les dates réellement tracées : Recharts positionne
// une ReferenceArea catégorielle par valeur d'axe, pas par échelle continue,
// donc x1/x2 doivent être des dates présentes dans `dates`, pas les bornes
// brutes de la phase.
export function phaseBands(phases: PhaseOut[], dates: string[]): PhaseBand[] {
  if (dates.length === 0) return [];
  const rangeStart = dates[0];
  const rangeEnd = dates[dates.length - 1];

  const bands: PhaseBand[] = [];
  for (const phase of phases) {
    if (phase.ends_on < rangeStart || phase.starts_on > rangeEnd) continue;
    const x1 = nearestDate(dates, phase.starts_on < rangeStart ? rangeStart : phase.starts_on);
    const x2 = nearestDate(dates, phase.ends_on > rangeEnd ? rangeEnd : phase.ends_on);
    if (x1 === undefined || x2 === undefined) continue;
    bands.push({ phaseId: phase.id, label: phase.name, x1, x2, color: KIND_COLOR[phase.kind] });
  }
  return bands;
}

function nearestDate(dates: string[], target: string): string | undefined {
  let nearest: string | undefined;
  let smallestDiff = Infinity;
  for (const date of dates) {
    const diff = Math.abs(Date.parse(date) - Date.parse(target));
    if (diff < smallestDiff) {
      smallestDiff = diff;
      nearest = date;
    }
  }
  return nearest;
}
