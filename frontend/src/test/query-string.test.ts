import { describe, it, expect } from "vitest";
import { buildQueryString } from "../lib/query-string";

describe("buildQueryString", () => {
  it("omits undefined and null values", () => {
    expect(buildQueryString({ a: 1, b: undefined, c: null })).toBe("?a=1");
  });

  it("formats a Date as YYYY-MM-DD", () => {
    expect(buildQueryString({ from: new Date(2026, 0, 5) })).toBe("?from=2026-01-05");
  });

  it("returns an empty string when there is nothing to serialize", () => {
    expect(buildQueryString({})).toBe("");
  });
});
