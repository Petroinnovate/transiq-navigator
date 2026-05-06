import axios from "axios";

// Create an axios instance with a prefilled base API URL
const axiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8001", // Base API URL - backend runs on port 8001
  timeout: 600000, // 10 minutes — pipeline makes many Gemini API calls per document
});

// Add request interceptor to include auth token
axiosInstance.interceptors.request.use(
  (config) => {
    // Get token from localStorage
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor: global error handling + 429 retry
axiosInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error.response?.status;

    if (status === 401) {
      // Token invalid or expired — clear storage and redirect to login
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user_data');
      if (window.location.pathname !== '/auth') {
        window.location.href = '/auth';
      }
    } else if (status === 403) {
      // Insufficient role — log for debugging; components surface this via toast
      console.error(
        `[API] 403 Forbidden — insufficient role for: ${error.config?.url}`
      );
    } else if (status === 404) {
      const url = error.config?.url ?? 'unknown';
      // Silence expected 404s from task-status polling (no Celery/Redis)
      if (!/\/task\//.test(url)) {
        console.error(
          `[API] 404 Not Found — requested resource not found: ${url}`
        );
      }
      error.message = `Requested resource not found. Please verify backend endpoint: ${url}`;
    } else if (status === 422) {
      // Validation error — log full detail so devs can see which field failed
      console.error('[API] 422 Validation Error:', error.response?.data);
    } else if (status === 429) {
      // Rate limited — wait for Retry-After header (or default 2 s) then retry once
      const retryAfter = Number(
        error.response?.headers?.['retry-after'] ?? 2
      );
      console.warn(`[API] 429 Rate limited — retrying after ${retryAfter}s`);
      await new Promise((r) => setTimeout(r, retryAfter * 1000));
      return axiosInstance.request(error.config);
    } else if (status >= 500) {
      console.error('[API] Server error:', error.response?.data);
    }

    return Promise.reject(error);
  }
);

// Add API version prefix helper
export const API_V2_BASE = '/api/v2';

export default axiosInstance;
