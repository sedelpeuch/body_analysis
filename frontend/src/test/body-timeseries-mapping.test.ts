import { describe, it, expect } from "vitest";
import { mergeTimeseries } from "../api/body/mapping";

describe("mergeTimeseries", () => {
  it("merges series sharing every date", () => {
    const merged = mergeTimeseries({
      weight: [{ at: "2026-01-01", value: 70 }, { at: "2026-01-02", value: 69.5 }],
      body_fat: [{ at: "2026-01-01", value: 15 }, { at: "2026-01-02", value: 14.8 }],
    });
    expect(merged).toEqual([
      { at: "2026-01-01", weight: 70, body_fat: 15 },
      { at: "2026-01-02", weight: 69.5, body_fat: 14.8 },
    ]);
  });

  it("fills a null when only one series has a point on a given date", () => {
    const merged = mergeTimeseries({
      weight: [{ at: "2026-01-01", value: 70 }, { at: "2026-01-03", value: 69 }],
      body_fat: [{ at: "2026-01-02", value: 14.8 }],
    });
    expect(merged).toEqual([
      { at: "2026-01-01", weight: 70, body_fat: null },
      { at: "2026-01-02", weight: null, body_fat: 14.8 },
      { at: "2026-01-03", weight: 69, body_fat: null },
    ]);
  });

  it("returns an empty array for empty input", () => {
    expect(mergeTimeseries({})).toEqual([]);
  });
});
