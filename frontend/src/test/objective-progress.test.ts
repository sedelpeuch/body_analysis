import { describe, it, expect } from "vitest";
import { objectiveProgress } from "../lib/objective-progress";

describe("objectiveProgress", () => {
  it("computes the fraction covered toward a 'down' objective", () => {
    expect(objectiveProgress("down", 72.9, 65.6, 65.0)).toBeCloseTo(7.3 / 7.9, 5);
  });

  it("clamps to 1 when the current value has overshot the target", () => {
    expect(objectiveProgress("down", 14.3, 10.8, 12.0)).toBe(1);
  });

  it("returns a binary 0/1 when the target was already on the wrong side of the start value", () => {
    // Masse musculaire déjà au-dessus d'une cible "à la hausse" au départ :
    // la distance parcourue depuis le départ n'a pas de sens, seule compte
    // l'atteinte actuelle de la cible.
    expect(objectiveProgress("up", 40.3, 37.7, 38.0)).toBe(0);
    expect(objectiveProgress("up", 40.3, 38.5, 38.0)).toBe(1);
  });

  it("returns 0 when the current value is null", () => {
    expect(objectiveProgress("down", 70, null, 65)).toBe(0);
  });

  it("resolves to achieved/not-achieved when there is no start value", () => {
    expect(objectiveProgress("down", null, 64, 65)).toBe(1);
    expect(objectiveProgress("down", null, 66, 65)).toBe(0);
  });
});
