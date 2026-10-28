export interface UserProfile {
  username: string;
  name: string | null;
  bio: string | null;
  location: string | null;
  company: string | null;
  blog: string | null;
  twitter_username: string | null;
  public_repos: number;
  followers: number;
  following: number;
  created_at: string;
  updated_at: string;
  avatar_url: string;
}

export interface Repository {
  id: number;
  name: string;
  full_name: string;
  description: string | null;
  language: string | null;
  stargazers_count: number;
  forks_count: number;
  is_fork: boolean;
  is_archived: boolean;
  html_url: string;
  updated_at: string;
  created_at: string;
  topics: string[];
}

export interface ContributionDay {
  date: string;
  count: number;
  level: number;
}

export interface ContributionWeek {
  first_day: string;
  days: ContributionDay[];
}

export interface ContributionHeatmap {
  weeks: ContributionWeek[];
  total_contributions: number;
}

export interface UserProfileResponse {
  profile: UserProfile;
  repos: Repository[] | null;
  contributions: ContributionHeatmap | null;
  cached_at: string;
  is_stale: boolean;
}

export interface PaginatedReposResponse {
  items: Repository[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface RepoFilters {
  language?: string;
  min_stars?: number;
  max_stars?: number;
  min_forks?: number;
  is_fork?: boolean;
  is_archived?: boolean;
  sort?: string;
  page?: number;
  per_page?: number;
}

export interface SyncResponse {
  status: "queued" | "completed";
  username: string;
  repos_synced?: number;
  synced_at?: string;
}

export interface HealthResponse {
  status: string;
  cache_users: number;
  cache_repos: number;
  cache_contributions: number;
}

export interface APIError {
  code: string;
  message: string;
  retry_after?: number;
  cached_at?: string;
}

export interface APIErrorResponse {
  error: APIError;
}