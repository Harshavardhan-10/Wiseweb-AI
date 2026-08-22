import type {
  Architecture,
  Comparison,
  Competitor,
  DeveloperReport,
  Evidence,
  ExecutiveReport,
  Finding,
  FindingStatus,
  Recommendation,
  Scan,
  ScanComparison,
  ScanProgress,
  TokenResponse,
  User,
  UserStats,
  Website,
  WebsiteCreate,
} from "./types";

export const ACCESS_KEY = "wisewebai.access";
export const REFRESH_KEY = "wisewebai.refresh";

const BASE =
  import.meta.env.VITE_API_URL ??
  import.meta.env.VITE_API_BASE_URL ??
  "/api/v1";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY);
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

function isRefreshTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split(".")[1] ?? ""));
    return typeof payload.exp === "number" && payload.exp * 1000 < Date.now();
  } catch {
    return true;
  }
}

async function refreshAccessToken(): Promise<string | null> {
  const refresh = localStorage.getItem(REFRESH_KEY);
  if (!refresh || isRefreshTokenExpired(refresh)) return null;
  try {
    const res = await fetch(`${BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) return null;
    const data = (await res.json()) as TokenResponse;
    setTokens(data.access_token, data.refresh_token);
    return data.access_token;
  } catch {
    return null;
  }
}

let refreshPromise: Promise<string | null> | null = null;

async function withAuthRetry(
  url: string,
  init: RequestInit,
  isAuthRoute: boolean,
): Promise<Response> {
  const res = await fetch(url, init);
  if (res.status !== 401 || isAuthRoute || init.method === "POST" && url.endsWith("/refresh")) {
    return res;
  }
  refreshPromise ??= refreshAccessToken().finally(() => {
    refreshPromise = null;
  });
  const token = await refreshPromise;
  if (!token) return res;
  const retry = await fetch(url, {
    ...init,
    headers: { ...init.headers, Authorization: `Bearer ${token}` },
  });
  return retry;
}

export async function api<T>(
  path: string,
  init: RequestInit = {},
  signal?: AbortSignal,
): Promise<T> {
  const isAuthRoute = path.startsWith("/auth");
  const token = getAccessToken();
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(init.headers as Record<string, string> | undefined),
  };
  if (init.body && typeof init.body === "string" && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  if (token && !isAuthRoute) headers.Authorization = `Bearer ${token}`;

  const res = await withAuthRetry(
    `${BASE}${path}`,
    { ...init, headers, signal },
    isAuthRoute,
  );

  if (res.status === 204) return undefined as T;

  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }

  if (!res.ok) {
    const detail =
      body && typeof body === "object" && "detail" in body
        ? (body as { detail: unknown }).detail
        : null;
    const err = {
      status: res.status,
      detail:
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? (detail as { msg?: string }[])
            : `Request failed (${res.status})`,
      raw: body,
    };
    throw err;
  }

  return body as T;
}

function jsonInit(method: string, body?: unknown): RequestInit {
  return { method, headers: { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body) };
}

export const apiClient = {
  // Auth
  login: (email: string, password: string) =>
    api<TokenResponse>("/auth/login", jsonInit("POST", { email, password })),
  register: (fullName: string, email: string, password: string) =>
    api<TokenResponse>("/auth/register", jsonInit("POST", { full_name: fullName, email, password })),
  me: () => api<User>("/auth/me"),

  // Users
  myStats: () => api<UserStats>("/users/me/stats"),

  // Websites
  listWebsites: () => api<Website[]>("/websites"),
  getWebsite: (id: number) => api<Website>(`/websites/${id}`),
  createWebsite: (payload: WebsiteCreate) =>
    api<Website>("/websites", jsonInit("POST", payload)),
  deleteWebsite: (id: number) => api<void>(`/websites/${id}`, { method: "DELETE" }),
  setMonitoring: (id: number, enabled: boolean) =>
    api<{ monitoring_enabled: boolean }>(
      `/websites/${id}/monitoring?enabled=${enabled}`,
      { method: "POST" },
    ),

  // Competitors
  listCompetitors: (websiteId: number) =>
    api<Competitor[]>(`/websites/${websiteId}/competitors`),
  addCompetitor: (websiteId: number, name: string, url: string) =>
    api<Competitor>(
      `/websites/${websiteId}/competitors`,
      jsonInit("POST", { name, url }),
    ),
  deleteCompetitor: (websiteId: number, competitorId: number) =>
    api<void>(`/websites/${websiteId}/competitors/${competitorId}`, { method: "DELETE" }),

  // Scans
  createScan: (websiteId: number, crawlDepth: number, pageLimit: number) =>
    api<Scan>(
      `/scans/websites/${websiteId}`,
      jsonInit("POST", { crawl_depth: crawlDepth, page_limit: pageLimit }),
    ),
  getScan: (scanId: number, signal?: AbortSignal) =>
    api<Scan>(`/scans/${scanId}`, {}, signal),
  scanProgress: (scanId: number, signal?: AbortSignal) =>
    api<ScanProgress>(`/scans/${scanId}/progress`, {}, signal),
  cancelScan: (scanId: number) => api<Scan>(`/scans/${scanId}/cancel`, { method: "POST" }),
  listWebsiteScans: (websiteId: number) =>
    api<{ items: Scan[]; total: number }>(`/scans/website/${websiteId}/list`),

  // Findings
  listFindings: (
    scanId: number,
    filters: { category?: string; severity?: string; status?: string },
    signal?: AbortSignal,
  ) => {
    const params = new URLSearchParams();
    if (filters.category) params.set("category", filters.category);
    if (filters.severity) params.set("severity", filters.severity);
    if (filters.status) params.set("status", filters.status);
    const qs = params.toString();
    return api<{ items: Finding[]; total: number }>(
      `/findings/scan/${scanId}${qs ? `?${qs}` : ""}`,
      {},
      signal,
    );
  },
  getFinding: (findingId: number) => api<Finding>(`/findings/${findingId}`),
  updateFindingStatus: (findingId: number, status: FindingStatus) =>
    api<Finding>(`/findings/${findingId}`, jsonInit("PATCH", { status })),
  findingEvidence: (findingId: number) => api<Evidence[]>(`/findings/${findingId}`),

  // Recommendations
  listRecommendations: (
    scanId: number,
    filters: { category?: string; priority?: string },
    signal?: AbortSignal,
  ) => {
    const params = new URLSearchParams();
    if (filters.category) params.set("category", filters.category);
    if (filters.priority) params.set("priority", filters.priority);
    const qs = params.toString();
    return api<{ items: Recommendation[]; total: number }>(
      `/recommendations/scan/${scanId}${qs ? `?${qs}` : ""}`,
      {},
      signal,
    );
  },
  updateRecommendationStatus: (recId: number, status: string) =>
    api<Recommendation>(`/recommendations/${recId}`, jsonInit("PATCH", { status })),

  // Architecture
  architecture: (scanId: number, signal?: AbortSignal) =>
    api<Architecture>(`/architecture/scan/${scanId}`, {}, signal),

  // Comparisons
  compare: (websiteId: number, competitorIds: number[], websiteIds: number[] = []) =>
    api<Comparison>(
      "/comparisons",
      jsonInit("POST", {
        website_id: websiteId,
        competitor_ids: competitorIds,
        website_ids: websiteIds,
      }),
    ),

  // Monitoring
  listChanges: (websiteId: number) =>
    api<ScanComparison[]>(`/websites/${websiteId}/changes`),
  compareScans: (websiteId: number, baseScanId: number, compareScanId: number) =>
    api<ScanComparison>(
      `/websites/${websiteId}/changes`,
      jsonInit("POST", { base_scan_id: baseScanId, compare_scan_id: compareScanId }),
    ),

  // Reports
  executiveReport: (scanId: number, signal?: AbortSignal) =>
    api<ExecutiveReport>(`/reports/scan/${scanId}/executive`, {}, signal),
  developerReport: (scanId: number, signal?: AbortSignal) =>
    api<DeveloperReport>(`/reports/scan/${scanId}/developer`, {}, signal),
};
