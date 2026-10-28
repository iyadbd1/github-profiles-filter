import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { PaginatedReposResponse, RepoFilters } from "../types/api";

export function useRepos(username: string, filters: RepoFilters, enabled = true) {
  return useQuery<PaginatedReposResponse, Error>({
    queryKey: ["repos", username, filters],
    queryFn: () => api.getRepos(username, filters),
    enabled: enabled && !!username,
    staleTime: 5 * 60 * 1000,
    retry: 2,
    retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 30000),
    placeholderData: (prev) => prev,
  });
}