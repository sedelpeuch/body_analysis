import { describe, it, expect } from "vitest";
import { phaseBands } from "../lib/phase-bands";
import type { PhaseOut } from "../api/types";

function phase(overrides: Partial<PhaseOut>): PhaseOut {
  return {
    id: 1,
    name: "Phase",
    kind: "cut",
    starts_on: "2026-01-01",
    ends_on: "2026-01-31",
    weight_target_kg: null,
    body_fat_target_pct: null,
    skeletal_muscle_target_kg: null,
    daily_calories_target: null,
    notes: null,
    ...overrides,
  };
}

const DATES = ["2026-01-05", "2026-01-10", "2026-01-15", "2026-01-20"];

describe("phaseBands", () => {
  it("clamps a phase that starts before the visible range to its first date", () => {
    const bands = phaseBands([phase({ starts_on: "2025-12-01", ends_on: "2026-01-10" })], DATES);
    expect(bands).toEqual([{ phaseId: 1, label: "Phase", x1: "2026-01-05", x2: "2026-01-10", color: "var(--color-accent-green)" }]);
  });

  it("drops a phase entirely outside the visible range", () => {
    const bands = phaseBands([phase({ starts_on: "2025-01-01", ends_on: "2025-02-01" })], DATES);
    expect(bands).toEqual([]);
  });

  it("returns nothing when there are no dates to anchor on", () => {
    expect(phaseBands([phase({})], [])).toEqual([]);
  });
});
