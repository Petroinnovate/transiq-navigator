// ============================================================================
// Legacy FastAPI axios client.
// ----------------------------------------------------------------------------
// HISTORY: This used to point at a FastAPI service running on localhost:8001
// during local dev. In Lovable / production that host is unreachable, so any
// call through this client fails with "Network Error".
//
// CURRENT STATE (Lovable Cloud port):
//   - The CORE pipeline (upload, processing, dashboard generation, search,
//     document history) has been ported to Supabase edge functions and is
//     consumed via `@/services/api` — see that file.
//   - The FOLLOWING modules still call this axios client and remain UNPORTED:
//       • src/api/ddrClient.ts          — DDR fleet/rig analytics (~30 endpoints)
//       • src/api/intelligenceClient.ts — entity intelligence
//       • src/api/sixSigmaClient.ts     — SPC analysis
//       • src/api/graphClient.ts        — graph RAG
//       • src/api/observabilityClient.ts — system health/MLOps
//       • src/api/dashboardApi.ts       — legacy dashboard endpoints
//
// FUTURE: When the FastAPI service is deployed (Google Cloud Run / Render /
// Railway), set the `VITE_API_URL` env var to its public HTTPS URL and these
// modules light up automatically — no further code changes needed.
//
// See MIGRATION.md at the repo root for the full migration plan.
// ============================================================================
import axios, { AxiosError } from "axios";

const RAW_API_URL = import.meta.env.VITE_API_URL?.trim();

/**
 * Returns true if VITE_API_URL is set to something that is actually reachable
 * from the browser (i.e. NOT localhost when the app is hosted on lovable.app).
 */
function isApiUrlUsable(): boolean {
  if (!RAW_API_URL) return false;
  // Localhost is only reachable when the frontend is also on localhost.
  const isLocalApi = /^https?:\/\/(localhost|127\.0\.0\.1)/i.test(RAW_API_URL);
  const isLocalHost = typeof window !== "undefined" &&
    /^(localhost|127\.0\.0\.1)$/i.test(window.location.hostname);
  if (isLocalApi && !isLocalHost) return false;
  return true;
}

export const isLegacyApiAvailable = isApiUrlUsable();

const axiosInstance = axios.create({
  baseURL: RAW_API_URL || "http://localhost:8001",
  timeout: 600000,
});

// Auth header injection (kept for forward compat — when FastAPI is deployed
// it may or may not honor this token; the source of truth for auth is now
// Supabase Auth).
axiosInstance.interceptors.request.use((config) => {
  if (!isLegacyApiAvailable) {
    // Short-circuit: don't even attempt the network call. Throw a clear,
    // user-meaningful error so feature pages can show "feature pending
    // Google Cloud migration" rather than confusing "Network Error".
    const url = `${config.baseURL ?? ""}${config.url ?? ""}`;
    const err = new AxiosError(
      `Legacy backend endpoint not available: ${url}. ` +
        `This module has not been ported to Lovable Cloud yet. ` +
        `Set VITE_API_URL to a deployed FastAPI service to enable it.`,
      "LEGACY_BACKEND_UNAVAILABLE",
      config as any,
    );
    return Promise.reject(err);
  }
  const token = localStorage.getItem("auth_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Response interceptor: keep existing error mapping for when the backend IS up.
axiosInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error.response?.status;
    if (status === 401) {
      localStorage.removeItem("auth_token");
      localStorage.removeItem("user_data");
      if (window.location.pathname !== "/auth") window.location.href = "/auth";
    } else if (status === 429) {
      const retryAfter = Number(error.response?.headers?.["retry-after"] ?? 2);
      await new Promise((r) => setTimeout(r, retryAfter * 1000));
      return axiosInstance.request(error.config);
    }
    return Promise.reject(error);
  },
);

export const API_V2_BASE = "/api/v2";
export default axiosInstance;
