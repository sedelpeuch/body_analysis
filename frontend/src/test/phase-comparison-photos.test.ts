import { describe, it, expect } from "vitest";
import { pickPhaseComparisonPhotos } from "../lib/phase-comparison-photos";
import type { PhotoOut } from "../api/types";

function photo(overrides: Partial<PhotoOut>): PhotoOut {
  return {
    id: 1,
    taken_on: "2026-01-01",
    tag: "face",
    width: null,
    height: null,
    byte_size: null,
    content_type: null,
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

const PREVIOUS_PHASE = { starts_on: "2026-01-01", ends_on: "2026-01-31" };
const CURRENT_PHASE = { starts_on: "2026-02-01", ends_on: "2026-02-28" };

describe("pickPhaseComparisonPhotos", () => {
  it("picks the latest photo of each phase per tag", () => {
    const photos = [
      photo({ id: 1, tag: "face", taken_on: "2026-01-05" }),
      photo({ id: 2, tag: "face", taken_on: "2026-01-20" }),
      photo({ id: 3, tag: "face", taken_on: "2026-02-10" }),
    ];
    const result = pickPhaseComparisonPhotos(photos, ["face"], PREVIOUS_PHASE, CURRENT_PHASE);
    expect(result).toEqual([{ tag: "face", before: photos[1], after: photos[2] }]);
  });

  it("returns null before when there is no previous phase", () => {
    const photos = [photo({ id: 1, tag: "face", taken_on: "2026-02-10" })];
    const result = pickPhaseComparisonPhotos(photos, ["face"], undefined, CURRENT_PHASE);
    expect(result).toEqual([{ tag: "face", before: null, after: photos[0] }]);
  });

  it("returns null for a tag with no photo in range", () => {
    const result = pickPhaseComparisonPhotos([], ["face"], PREVIOUS_PHASE, CURRENT_PHASE);
    expect(result).toEqual([{ tag: "face", before: null, after: null }]);
  });
});
