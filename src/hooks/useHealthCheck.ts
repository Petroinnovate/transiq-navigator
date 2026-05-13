import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { isLegacyApiAvailable } from "@/lib/axios";
import axios from "@/lib/axios";

type HealthStatus = "healthy" | "critical" | "unknown";

interface HealthCheckResult {
  status: HealthStatus;
  isHealthy: boolean;
  isCritical: boolean;
  /** Whether the legacy FastAPI backend is configured and reachable. */
  legacyBackendOnline: boolean;
}

/**
 * Lovable Cloud health: a lightweight Supabase ping. If Supabase responds we
 * consider the platform healthy — the core pipeline (upload / extract /
 * dashboard / search) lives in edge functions and uses Supabase as its
 * datastore, so a healthy Supabase = healthy core.
 *
 * The legacy FastAPI backend (DDR, intelligence, six-sigma, graph,
 * observability) is checked separately and surfaced as `legacyBackendOnline`.
 */
async function fetchHealth(): Promise<{
  cloud: HealthStatus;
  legacy: boolean;
}> {
  let cloud: HealthStatus = "critical";
  try {
    // Unauthenticated health probe — works regardless of RLS / login state.
    const url = import.meta.env.VITE_SUPABASE_URL;
    const res = await fetch(`${url}/auth/v1/health`, {
      headers: { apikey: import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY },
    });
    cloud = res.ok ? "healthy" : "critical";
  } catch {
    cloud = "critical";
  }

  let legacy = false;
  if (isLegacyApiAvailable) {
    try {
      const { data } = await axios.get("/health", { timeout: 5000 });
      legacy = data?.status === "ok" || data?.status === "healthy";
    } catch {
      legacy = false;
    }
  }

  return { cloud, legacy };
}

export function useHealthCheck(): HealthCheckResult {
  const { data } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 30_000,
    staleTime: 25_000,
    retry: 1,
  });

  const status: HealthStatus = data?.cloud ?? "unknown";
  return {
    status,
    isHealthy: status === "healthy",
    isCritical: status === "critical",
    legacyBackendOnline: data?.legacy ?? false,
  };
}
