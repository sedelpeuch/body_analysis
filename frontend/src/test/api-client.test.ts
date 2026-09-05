import { describe, it, expect, vi, afterEach } from "vitest";
import { request, ApiError } from "../api/client";

afterEach(() => vi.restoreAllMocks());

describe("request", () => {
  it("returns the parsed JSON body on success", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), { status: 200 }),
    ));
    await expect(request<{ status: string }>("/health")).resolves.toEqual({ status: "ok" });
  });

  it("throws an ApiError carrying the ProblemDetails on a non-2xx response", async () => {
    const problem = { type: "about:blank", title: "Ressource introuvable", status: 404, detail: "Phase 9 introuvable", instance: "/api/phases/9" };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(JSON.stringify(problem), { status: 404 }),
    ));
    await expect(request("/phases/9")).rejects.toBeInstanceOf(ApiError);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(JSON.stringify(problem), { status: 404 }),
    ));
    await expect(request("/phases/9")).rejects.toMatchObject({ status: 404, problem });
  });
});
