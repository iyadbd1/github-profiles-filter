import { useMutation } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { RepoFilters } from "../types/api";

export function useExport() {
  return useMutation({
    mutationFn: async ({
      username,
      filters,
      format,
    }: {
      username: string;
      filters: RepoFilters;
      format: "csv" | "json";
    }) => {
      const blob = await api.exportRepos(username, filters, format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `github-repos-${username}-${Date.now()}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
  });
}