import axios from "axios";

/**
 * Zentraler API-Client. `withCredentials: true`, da der Auth-Token ab
 * Phase 1 als httpOnly-Cookie gesetzt wird (kein Token in localStorage -
 * schützt vor Auslesen per XSS).
 */
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  withCredentials: true,
});
