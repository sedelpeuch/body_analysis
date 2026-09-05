import { describe, it, expect } from "vitest";
import { measurementsQueryKey } from "../api/body/hooks";

describe("measurementsQueryKey", () => {
  it("varies with the date range so two ranges never share a cache entry", () => {
    const a = measurementsQueryKey({ from: "2026-01-01", to: "2026-01-31" });
    const b = measurementsQueryKey({ from: "2026-02-01", to: "2026-02-28" });
    expect(a).not.toEqual(b);
  });
});
