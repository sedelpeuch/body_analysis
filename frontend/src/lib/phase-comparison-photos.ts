import type { PhotoOut } from "../api/types";

export interface PhaseComparisonEntry {
  tag: string;
  before: PhotoOut | null;
  after: PhotoOut | null;
}

export interface PhaseRange {
  starts_on: string;
  ends_on: string;
}

// Pour chaque tag, la dernière photo de la phase précédente ("avant") contre
// la dernière photo de la phase en cours ("après") — pas "aujourd'hui", qui
// n'a pas de sens pour un usage où les données sont importées par lots.
export function pickPhaseComparisonPhotos(
  photos: PhotoOut[],
  tags: readonly string[],
  previousPhase: PhaseRange | undefined,
  currentPhase: PhaseRange,
): PhaseComparisonEntry[] {
  return tags.map((tag) => {
    const forTag = photos.filter((p) => p.tag === tag);
    return {
      tag,
      before: previousPhase ? latestInRange(forTag, previousPhase) : null,
      after: latestInRange(forTag, currentPhase),
    };
  });
}

function latestInRange(photos: PhotoOut[], range: PhaseRange): PhotoOut | null {
  const inRange = photos.filter((p) => p.taken_on >= range.starts_on && p.taken_on <= range.ends_on);
  if (inRange.length === 0) return null;
  return inRange.reduce((latest, p) => (p.taken_on > latest.taken_on ? p : latest));
}
