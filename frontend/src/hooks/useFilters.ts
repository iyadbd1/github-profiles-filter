import { useSearchParams } from "react-router-dom";
import { useMemo, useCallback } from "react";
import type { RepoFilters } from "../types/api";

const FILTER_KEYS = [
  "language",
  "min_stars",
  "max_stars",
  "min_forks",
  "is_fork",
  "is_archived",
  "sort",
  "page",
  "per_page",
] as const;

function parseFilters(searchParams: URLSearchParams): RepoFilters {
  const filters: RepoFilters = {};
  FILTER_KEYS.forEach((key) => {
    const value = searchParams.get(key);
    if (value !== null) {
      if (key === "page" || key === "per_page" || key === "min_stars" || key === "max_stars" || key === "min_forks") {
        (filters as any)[key] = parseInt(value, 10);
      } else if (key === "is_fork" || key === "is_archived") {
        (filters as any)[key] = value === "true";
      } else {
        (filters as any)[key] = value;
      }
    }
  });
  return filters;
}

function serializeFilters(filters: RepoFilters): Record<string, string> {
  const params: Record<string, string> = {};
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      params[key] = String(value);
    }
  });
  return params;
}

export function useFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo(() => parseFilters(searchParams), [searchParams]);

  const setFilters = useCallback((next: Partial<RepoFilters>) => {
    setSearchParams((prev) => {
      const merged = { ...parseFilters(prev), ...next };
      const params = new URLSearchParams();
      Object.entries(serializeFilters(merged)).forEach(([k, v]) => params.set(k, v));
      return params;
    });
  }, [setSearchParams]);

  const resetFilters = useCallback(() => {
    setSearchParams({});
  }, [setSearchParams]);

  return { filters, setFilters, resetFilters };
}