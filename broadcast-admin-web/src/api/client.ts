import axios from "axios";

// Use relative URL when running in production (proxied by nginx)
// Use direct URL for development (when VITE_BROADCAST_API_URL is set)
const API_URL = import.meta.env.VITE_BROADCAST_API_URL || "/api";
const STORAGE_KEY = "broadcastAdminApiKey";


export const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 15000,
});

apiClient.interceptors.request.use((config) => {
  const apiKey = sessionStorage.getItem(STORAGE_KEY);
  if (apiKey) {
    config.headers = config.headers ?? {};
    config.headers["x-admin-api-key"] = apiKey;
  }
  return config;
});

export const apiSettings = {
  STORAGE_KEY,
  API_URL,
};

