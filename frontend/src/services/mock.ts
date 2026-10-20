import type {
  Api,
  AuthResponse,
  DailyClicks,
  Link,
  LinkCreate,
  LinkStats,
  TokenStore,
  User,
} from "./types";
import { ApiError } from "./types";

/** In-memory backend that follows the same rules as the real one (see _docs/plan.md).
 * The UI is built and tested against it; `npm run dev:mock` runs the app with it. */

const RESERVED = new Set(["api", "app", "login", "signup", "health", "metrics", "static", "assets", "docs"]);
const ALIAS_RE = /^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/;
const BASE = "http://localhost:8000";

interface Account {
  user: User;
  password: string;
}

interface StoredLink extends Link {
  owner_id: number;
  deleted: boolean;
}

function validationError(field: string, message: string): ApiError {
  return new ApiError(422, message, [{ field, message }]);
}

function randomCode(): string {
  const alphabet = "abcdefghijklmnopqrstuvwxyz0123456789";
  return Array.from({ length: 7 }, () => alphabet[Math.floor(Math.random() * alphabet.length)]).join("");
}

function statusOf(link: StoredLink): Link["status"] {
  if (!link.is_active) return "disabled";
  if (link.expires_at && new Date(link.expires_at) <= new Date()) return "expired";
  return "active";
}

function publicLink(link: StoredLink): Link {
  const { owner_id: _owner, deleted: _deleted, ...rest } = link;
  return { ...rest, status: statusOf(link) };
}

export function createMockApi(tokens: TokenStore, options: { seed?: boolean } = {}): Api {
  const accounts: Account[] = [];
  const links: StoredLink[] = [];
  const stats = new Map<number, LinkStats>();
  let nextUserId = 1;
  let nextLinkId = 1;

  function issue(user: User): AuthResponse {
    const token = `mock-token-${user.id}`;
    return { access_token: token, token_type: "bearer", user };
  }

  function currentUser(): User {
    const token = tokens.get();
    const id = token?.startsWith("mock-token-") ? Number(token.slice(11)) : NaN;
    const account = accounts.find((a) => a.user.id === id);
    if (!account) {
      tokens.set(null);
      throw new ApiError(401, "Not authenticated");
    }
    return account.user;
  }

  function ownLink(id: number): StoredLink {
    const user = currentUser();
    const link = links.find((l) => l.id === id && l.owner_id === user.id && !l.deleted);
    if (!link) throw new ApiError(404, "Link not found");
    return link;
  }

  function emptyDaily(days: number): DailyClicks[] {
    const today = new Date();
    return Array.from({ length: days }, (_, i) => {
      const d = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate() - (days - 1 - i)));
      return { date: d.toISOString().slice(0, 10), clicks: 0, unique_visitors: 0 };
    });
  }

  const delay = <T>(value: T): Promise<T> => new Promise((resolve) => setTimeout(() => resolve(value), 30));

  const api: Api = {
    async signup(email, password) {
      email = email.trim().toLowerCase();
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) throw validationError("email", "Enter a valid email address");
      if (password.length < 8) throw validationError("password", "Password must be at least 8 characters");
      if (accounts.some((a) => a.user.email === email)) {
        throw new ApiError(409, "An account with this email already exists");
      }
      const user = { id: nextUserId++, email, created_at: new Date().toISOString() };
      accounts.push({ user, password });
      return delay(issue(user));
    },

    async login(email, password) {
      const account = accounts.find((a) => a.user.email === email.trim().toLowerCase());
      if (!account || account.password !== password) throw new ApiError(401, "Wrong email or password");
      return delay(issue(account.user));
    },

    async me() {
      return delay(currentUser());
    },

    async listLinks(page = 1, pageSize = 20) {
      const user = currentUser();
      const own = links.filter((l) => l.owner_id === user.id && !l.deleted).sort((a, b) => b.id - a.id);
      const items = own.slice((page - 1) * pageSize, page * pageSize).map(publicLink);
      return delay({ items, total: own.length, page, page_size: pageSize });
    },

    async createLink(body: LinkCreate) {
      const user = currentUser();
      const url = body.target_url.trim();
      if (!/^https?:\/\/[^\s/]+/i.test(url)) {
        throw validationError("target_url", "Only http and https URLs can be shortened");
      }
      if (body.expires_at && new Date(body.expires_at) <= new Date()) {
        throw validationError("expires_at", "Expiration must be in the future");
      }
      let code = randomCode();
      const alias = body.alias?.trim().toLowerCase();
      if (alias) {
        if (alias.length < 3 || alias.length > 32) throw validationError("alias", "Alias must be 3 to 32 characters long");
        if (!ALIAS_RE.test(alias)) {
          throw validationError("alias", "Alias may contain only letters, digits and '-', and cannot start or end with '-'");
        }
        if (RESERVED.has(alias)) throw validationError("alias", `Alias '${alias}' is reserved`);
        if (links.some((l) => l.code === alias)) throw new ApiError(409, "This alias is already taken");
        code = alias;
      }
      const link: StoredLink = {
        id: nextLinkId++,
        code,
        short_url: `${BASE}/${code}`,
        target_url: url,
        status: "active",
        is_active: true,
        expires_at: body.expires_at ?? null,
        created_at: new Date().toISOString(),
        total_clicks: 0,
        owner_id: user.id,
        deleted: false,
      };
      links.push(link);
      return delay(publicLink(link));
    },

    async getLink(id) {
      return delay(publicLink(ownLink(id)));
    },

    async setLinkActive(id, isActive) {
      const link = ownLink(id);
      link.is_active = isActive;
      return delay(publicLink(link));
    },

    async deleteLink(id) {
      const link = ownLink(id);
      link.deleted = true;
      stats.delete(id);
      return delay(undefined);
    },

    async getStats(id, days = 30) {
      const link = ownLink(id);
      const known = stats.get(id);
      const daily = emptyDaily(days);
      if (known) {
        for (const d of known.daily) {
          const slot = daily.find((x) => x.date === d.date);
          if (slot) Object.assign(slot, d);
        }
      }
      return delay({
        link_id: link.id,
        total_clicks: link.total_clicks,
        daily,
        referrers: known?.referrers ?? [],
        countries: known?.countries ?? [],
      });
    },
  };

  if (options.seed) {
    const demo = { id: nextUserId++, email: "demo@example.com", created_at: new Date().toISOString() };
    accounts.push({ user: demo, password: "demo-password" });
    const seeded: StoredLink = {
      id: nextLinkId++,
      code: "demo-talk",
      short_url: `${BASE}/demo-talk`,
      target_url: "https://example.com/slides/system-design-talk",
      status: "active",
      is_active: true,
      expires_at: null,
      created_at: new Date().toISOString(),
      total_clicks: 57,
      owner_id: demo.id,
      deleted: false,
    };
    links.push(seeded);
    const daily = emptyDaily(30).map((d, i) => {
      const clicks = i < 20 ? 0 : [3, 5, 2, 8, 12, 6, 4, 9, 5, 3][i - 20];
      return { ...d, clicks, unique_visitors: Math.ceil(clicks * 0.7) };
    });
    stats.set(seeded.id, {
      link_id: seeded.id,
      total_clicks: 57,
      daily,
      referrers: [
        { name: "t.me", clicks: 31 },
        { name: "direct", clicks: 17 },
        { name: "linkedin.com", clicks: 9 },
      ],
      countries: [
        { name: "RU", clicks: 38 },
        { name: "DE", clicks: 11 },
        { name: "unknown", clicks: 8 },
      ],
    });
  }

  return api;
}
