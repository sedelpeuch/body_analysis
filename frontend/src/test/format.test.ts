import { describe, it, expect } from "vitest";
import { formatDuration, formatPace, formatDelta } from "../lib/format";

describe("formatDuration", () => {
  it("formats milliseconds as H:MM:SS", () => {
    expect(formatDuration(3_725_000)).toBe("1:02:05");
  });
  it("omits the hour segment under an hour", () => {
    expect(formatDuration(65_000)).toBe("1:05");
  });
});

describe("formatPace", () => {
  it("formats seconds-per-km as MM:SS/km", () => {
    expect(formatPace(330)).toBe("5:30/km");
  });
  it("renders the empty-value dash for a null pace", () => {
    expect(formatPace(null)).toBe("—");
  });
});

describe("formatDelta", () => {
  it("prefixes a positive change with +", () => {
    expect(formatDelta(1.2, "kg")).toBe("+1.2 kg");
  });
  it("prefixes a negative change with the minus sign, not a hyphen", () => {
    expect(formatDelta(-1.2, "kg")).toBe("−1.2 kg");
  });
  it("renders the empty-value dash for a null delta", () => {
    expect(formatDelta(null, "kg")).toBe("—");
  });
});
