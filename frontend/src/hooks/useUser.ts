import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { UserProfileResponse } from "../types/api";

export function useUser(username: string, enabled = true) {
  return useQuery<UserProfileResponse, Error>({
    queryKey: ["user", username],
    queryFn: () => api.getUser(username, true, true),
    enabled: enabled && !!username,
    staleTime: 5 * 60 * 1000,
    retry: 2,
    retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 30000),
  });
}