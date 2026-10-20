// Types mirror the schemas in /openapi.yaml. Change the contract first, then these.

export interface User {
  id: number;
  email: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: "bearer";
  user: User;
}

export type LinkStatus = "active" | "disabled" | "expired";

export interface Link {
  id: number;
  code: string;
  short_url: string;
  target_url: string;
  status: LinkStatus;
  is_active: boolean;
  expires_at: string | null;
  created_at: string;
  total_clicks: number;
}

export interface LinkPage {
  items: Link[];
  total: number;
  page: number;
  page_size: number;
}

export interface LinkCreate {
  target_url: string;
  alias?: string | null;
  expires_at?: string | null;
}

export interface DailyClicks {
  date: string;
  clicks: number;
  unique_visitors: number;
}

export interface NamedCount {
  name: string;
  clicks: number;
}

export interface LinkStats {
  link_id: number;
  total_clicks: number;
  daily: DailyClicks[];
  referrers: NamedCount[];
  countries: NamedCount[];
}

export interface FieldError {
  field: string;
  message: string;
}

/** Every failed call rejects with this; `detail` is ready to show to the user. */
export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
    public errors: FieldError[] = [],
  ) {
    super(detail);
    this.name = "ApiError";
  }

  fieldError(field: string): string | undefined {
    return this.errors.find((e) => e.field === field)?.message;
  }
}

/** The whole backend as the UI sees it. `mock.ts` and `http.ts` both implement it. */
export interface Api {
  signup(email: string, password: string): Promise<AuthResponse>;
  login(email: string, password: string): Promise<AuthResponse>;
  me(): Promise<User>;
  listLinks(page?: number, pageSize?: number): Promise<LinkPage>;
  createLink(body: LinkCreate): Promise<Link>;
  getLink(id: number): Promise<Link>;
  setLinkActive(id: number, isActive: boolean): Promise<Link>;
  deleteLink(id: number): Promise<void>;
  getStats(id: number, days?: number): Promise<LinkStats>;
}

export interface TokenStore {
  get(): string | null;
  set(token: string | null): void;
}
