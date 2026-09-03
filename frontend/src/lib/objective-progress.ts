import type { Direction } from "../api/types";

function isAchieved(direction: Direction, current: number, target: number): boolean {
  return direction === "down" ? current <= target : current >= target;
}

// Fraction [0,1] de progression vers un objectif de phase, prenant en
// compte le sens d'atteinte. Ne présume jamais que `start` et `target` sont
// du même côté (une masse musculaire peut démarrer déjà au-dessus d'une
// cible "à la hausse" — auquel cas la distance parcourue depuis le départ
// n'a pas de sens : seule compte l'atteinte, binaire, de la cible).
export function objectiveProgress(
  direction: Direction,
  start: number | null,
  current: number | null,
  target: number,
): number {
  if (current === null) return 0;
  const achieved = isAchieved(direction, current, target);
  if (start === null) return achieved ? 1 : 0;

  const totalNeeded = direction === "down" ? start - target : target - start;
  if (totalNeeded <= 0) return achieved ? 1 : 0;

  const progressed = direction === "down" ? start - current : current - start;
  return Math.min(1, Math.max(0, progressed / totalNeeded));
}
