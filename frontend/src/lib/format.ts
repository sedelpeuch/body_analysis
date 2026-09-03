export function formatDuration(ms: number): string {
  const totalSeconds = Math.round(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const paddedSeconds = String(seconds).padStart(2, "0");
  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${paddedSeconds}`;
  }
  return `${minutes}:${paddedSeconds}`;
}

export function formatPace(secondsPerKm: number | null): string {
  if (secondsPerKm === null) return "—";
  const minutes = Math.floor(secondsPerKm / 60);
  const seconds = Math.round(secondsPerKm % 60);
  return `${minutes}:${String(seconds).padStart(2, "0")}/km`;
}

export function formatDelta(value: number | null, unit: string): string {
  if (value === null) return "—";
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  const magnitude = Math.abs(value).toFixed(1);
  return `${sign}${magnitude} ${unit}`;
}

// Étiquette d'axe X pour un graphique temporel : un ISO 8601 complet
// ("2026-08-31T10:37:18.913000Z", l'horodatage brut d'un échantillon de
// séance) devient "10:37" ; une date seule ("2026-08-31", un point
// quotidien) devient "31/08" ; toute autre valeur (heure de repas, nom de
// phase...) reste inchangée.
export function formatAxisTick(value: string): string {
  const isoDateTime = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/;
  const isoDate = /^\d{4}-(\d{2})-(\d{2})$/;
  if (isoDateTime.test(value)) {
    return value.slice(11, 16);
  }
  const dateMatch = value.match(isoDate);
  if (dateMatch) {
    return `${dateMatch[2]}/${dateMatch[1]}`;
  }
  return value;
}
