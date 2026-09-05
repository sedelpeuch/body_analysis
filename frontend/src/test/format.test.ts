import { describe, it, expect } from "vitest";
import { formatDuration, formatPace, formatDelta, formatAxisTick } from "../lib/format";

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

describe("formatAxisTick", () => {
  it("shortens a full ISO datetime to HH:MM", () => {
    expect(formatAxisTick("2026-08-31T10:37:18.913000Z")).toBe("10:37");
  });
  it("shortens an ISO date to DD/MM", () => {
    expect(formatAxisTick("2026-08-31")).toBe("31/08");
  });
  it("leaves any other tick value unchanged", () => {
    expect(formatAxisTick("6h")).toBe("6h");
  });
});
