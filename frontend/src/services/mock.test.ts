import { describe, expect, it } from "vitest";
import { createMockApi } from "./mock";
import { ApiError } from "./types";
import { memoryTokens } from "../test-utils";

async function loggedIn() {
  const tokens = memoryTokens();
  const api = createMockApi(tokens);
  const { access_token } = await api.signup("owner@example.com", "long-enough");
  tokens.set(access_token);
  return api;
}

describe("mock backend follows the API rules", () => {
  it("rejects a duplicate email", async () => {
    const api = createMockApi(memoryTokens());
    await api.signup("a@example.com", "long-enough");
    await expect(api.signup("A@example.com", "long-enough")).rejects.toMatchObject({ status: 409 });
  });

  it("requires a token for links", async () => {
    const api = createMockApi(memoryTokens());
    await expect(api.listLinks()).rejects.toMatchObject({ status: 401 });
  });

  it("validates aliases like the backend", async () => {
    const api = await loggedIn();
    for (const alias of ["api", "-bad", "ab"]) {
      const error = await api.createLink({ target_url: "https://example.com", alias }).catch((e) => e);
      expect(error).toBeInstanceOf(ApiError);
      expect(error.status).toBe(422);
      expect(error.fieldError("alias")).toBeTruthy();
    }
  });

  it("rejects non-http URLs", async () => {
    const api = await loggedIn();
    const error = await api.createLink({ target_url: "ftp://example.com" }).catch((e) => e);
    expect(error.fieldError("target_url")).toMatch(/http/);
  });

  it("creates, disables and deletes a link", async () => {
    const api = await loggedIn();
    const link = await api.createLink({ target_url: "https://example.com", alias: "My-Talk" });
    expect(link.code).toBe("my-talk");
    expect((await api.setLinkActive(link.id, false)).status).toBe("disabled");
    await api.deleteLink(link.id);
    expect((await api.listLinks()).total).toBe(0);
    await expect(api.getLink(link.id)).rejects.toMatchObject({ status: 404 });
  });

  it("returns zero-filled stats for the requested window", async () => {
    const api = await loggedIn();
    const link = await api.createLink({ target_url: "https://example.com" });
    const stats = await api.getStats(link.id, 7);
    expect(stats.daily).toHaveLength(7);
    expect(stats.daily.every((d) => d.clicks === 0)).toBe(true);
  });
});
