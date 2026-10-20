import { createHttpApi } from "./http";
import { createMockApi } from "./mock";
import type { Api, TokenStore } from "./types";

export * from "./types";

const TOKEN_KEY = "shortly.token";

export const tokenStore: TokenStore = {
  get() {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set(token) {
    try {
      if (token) localStorage.setItem(TOKEN_KEY, token);
      else localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* storage unavailable: the session lasts until reload */
    }
  },
};

/** The one switch between the fake and the real backend: VITE_API_MODE=mock|http. */
export function createApi(tokens: TokenStore = tokenStore): Api {
  return import.meta.env.VITE_API_MODE === "mock"
    ? createMockApi(tokens, { seed: true })
    : createHttpApi(tokens);
}
