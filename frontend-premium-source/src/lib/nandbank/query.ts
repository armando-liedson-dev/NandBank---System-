import { useQuery } from "@tanstack/react-query";

import { DEMO_MODE } from "@/services/api/client";

export async function resolveNandQuery<T>(
  demoMode: boolean,
  demoData: T | undefined,
  queryFn: () => Promise<T>,
): Promise<T> {
  if (demoMode && demoData !== undefined) return demoData;
  return queryFn();
}

export function useNandQuery<T>(
  key: readonly unknown[],
  queryFn: () => Promise<T>,
  demoData?: T,
) {
  return useQuery({
    queryKey: [...key, DEMO_MODE ? "demo" : "live"],
    queryFn: () => resolveNandQuery(DEMO_MODE, demoData, queryFn),
    enabled: typeof window !== "undefined",
    retry: false,
    staleTime: 15_000,
    refetchOnWindowFocus: false,
  });
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Não foi possível carregar esta informação.";
}