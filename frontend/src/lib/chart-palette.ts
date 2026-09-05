// Palette catégorielle des séries de graphiques, dérivée de l'accent double
// (vert/bleu) et des couleurs de domaine, validée par le script dataviz
// (bande de luminosité OKLCH sombre, séparation CVD, contraste vs surface
// #12161a). Ordre fixe — jamais recyclé selon un filtre actif : une série
// garde sa couleur même si d'autres disparaissent du graphique.
const SERIES_COLORS = [
  "#1a9f5f", // vert — variante graphique de l'accent primaire (entraînement)
  "#2e8fe0", // bleu — accent secondaire (corps)
  "#b8842e", // ambre — variante graphique de la couleur nutrition
  "#a06de0", // violet — couleur phases
] as const;

const FALLBACK_COLOR = "#5b656b"; // text-low : au-delà de 4 séries, replier plutôt qu'inventer une teinte

export function seriesColor(index: number): string {
  return SERIES_COLORS[index] ?? FALLBACK_COLOR;
}
