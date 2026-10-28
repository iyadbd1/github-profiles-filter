import type {
  UserProfileResponse,
  PaginatedReposResponse,
  RepoFilters,
  SyncResponse,
  HealthResponse,
  APIErrorResponse,
} from "../types/api";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api/v1";
const API_KEY = import.meta.env.VITE_API_KEY || "";

async function fetchWithAuth<T>(url: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error: APIErrorResponse = await response.json().catch(() => ({
      error: { code: "UNKNOWN", message: response.statusText },
    }));
    throw new APIError(error.error);
  }

  return response.json();
}

export class APIError extends Error {
  code: string;
  retryAfter?: number;
  cachedAt?: string;

  constructor(error: { code: string; message: string; retry_after?: number; cached_at?: string }) {
    super(error.message);
    this.name = "APIError";
    this.code = error.code;
    this.retryAfter = error.retry_after;
    this.cachedAt = error.cached_at;
  }
}

export const api = {
  async getUser(username: string, includeRepos = true, includeContributions = true): Promise<UserProfileResponse> {
    const params = new URLSearchParams({
      include_repos: String(includeRepos),
      include_contributions: String(includeContributions),
    });
    return fetchWithAuth(`${API_BASE}/users/${encodeURIComponent(username)}?${params}`);
  },

  async getRepos(username: string, filters: RepoFilters = {}): Promise<PaginatedReposResponse> {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        params.append(key, String(value));
      }
    });
    return fetchWithAuth(`${API_BASE}/users/${encodeURIComponent(username)}/repos?${params}`);
  },

  async exportRepos(username: string, filters: RepoFilters, format: "csv" | "json" = "csv"): Promise<Blob> {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        params.append(key, String(value));
      }
    });
    params.append("format", format);
    const response = await fetch(`${API_BASE}/users/${encodeURIComponent(username)}/export?${params}`, {
      headers: { "X-API-Key": API_KEY },
    });
    if (!response.ok) {
      const error: APIErrorResponse = await response.json().catch(() => ({
        error: { code: "UNKNOWN", message: response.statusText },
      }));
      throw new APIError(error.error);
    }
    return response.blob();
  },

  async syncUser(username: string, force = false): Promise<SyncResponse> {
    return fetchWithAuth(`${API_BASE}/sync/${encodeURIComponent(username)}`, {
      method: "POST",
      body: JSON.stringify({ force }),
    });
  },

  async health(): Promise<HealthResponse> {
    return fetchWithAuth(`${API_BASE}/health`);
  },
};