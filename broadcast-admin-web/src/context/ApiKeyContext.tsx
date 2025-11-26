import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";

import { apiSettings } from "../api/client";

interface ApiKeyContextValue {
  apiKey: string | null;
  setApiKey: (value: string) => void;
  clearApiKey: () => void;
}

const ApiKeyContext = createContext<ApiKeyContextValue | undefined>(undefined);

export const ApiKeyProvider = ({ children }: PropsWithChildren) => {
  const [apiKey, setApiKeyState] = useState<string | null>(() => {
    return localStorage.getItem(apiSettings.STORAGE_KEY);
  });

  const setApiKey = useCallback((value: string) => {
    localStorage.setItem(apiSettings.STORAGE_KEY, value);
    setApiKeyState(value);
  }, []);

  const clearApiKey = useCallback(() => {
    localStorage.removeItem(apiSettings.STORAGE_KEY);
    setApiKeyState(null);
  }, []);

  const value = useMemo<ApiKeyContextValue>(
    () => ({ apiKey, setApiKey, clearApiKey }),
    [apiKey, clearApiKey, setApiKey],
  );

  return <ApiKeyContext.Provider value={value}>{children}</ApiKeyContext.Provider>;
};

export const useApiKey = () => {
  const ctx = useContext(ApiKeyContext);
  if (!ctx) {
    throw new Error("useApiKey must be used within ApiKeyProvider");
  }
  return ctx;
};

