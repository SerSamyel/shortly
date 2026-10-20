import type {
  Api,
  AuthResponse,
  FieldError,
  Link,
  LinkCreate,
  LinkPage,
  LinkStats,
  TokenStore,
  User,
} from "./types";
import { ApiError } from "./types";

/** The real backend client. Same-origin: the backend serves this app in production,
 * and Vite proxies /api to it in development. */
export function createHttpApi(tokens: TokenStore, baseUrl = ""): Api {
  async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const headers: Record<string, string> = { Accept: "application/json" };
    const token = tokens.get();
    if (token) headers.Authorization = `Bearer ${token}`;
    if (body !== undefined) headers["Content-Type"] = "application/json";

    let response: Response;
    try {
      response = await fetch(`${baseUrl}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch {
      throw new ApiError(0, "Cannot reach the server. Check your connection and try again.");
    }

    if (response.status === 204) return undefined as T;
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      if (response.status === 401) tokens.set(null);
      const detail =
        (data && typeof data.detail === "string" && data.detail) ||
        `Request failed (${response.status})`;
      const errors: FieldError[] = Array.isArray(data?.errors) ? data.errors : [];
      throw new ApiError(response.status, detail, errors);
    }
    return data as T;
  }

  return {
    signup: (email, password) =>
      request<AuthResponse>("POST", "/api/auth/signup", { email, password }),
    login: (email, password) =>
      request<AuthResponse>("POST", "/api/auth/login", { email, password }),
    me: () => request<User>("GET", "/api/auth/me"),
    listLinks: (page = 1, pageSize = 20) =>
      request<LinkPage>("GET", `/api/links?page=${page}&page_size=${pageSize}`),
    createLink: (body: LinkCreate) => request<Link>("POST", "/api/links", body),
    getLink: (id) => request<Link>("GET", `/api/links/${id}`),
    setLinkActive: (id, isActive) =>
      request<Link>("PATCH", `/api/links/${id}`, { is_active: isActive }),
    deleteLink: (id) => request<void>("DELETE", `/api/links/${id}`),
    getStats: (id, days = 30) => request<LinkStats>("GET", `/api/links/${id}/stats?days=${days}`),
  };
}
