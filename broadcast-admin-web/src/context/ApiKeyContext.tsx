import {
  useCallback,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";

import { apiSettings } from "../api/client";

import { ApiKeyContext, type ApiKeyContextValue } from "./apiKey";

export const ApiKeyProvider = ({ children }: PropsWithChildren) => {
  const [apiKey, setApiKeyState] = useState<string | null>(() => {
    return sessionStorage.getItem(apiSettings.STORAGE_KEY);
  });

  const setApiKey = useCallback((value: string) => {
    sessionStorage.setItem(apiSettings.STORAGE_KEY, value);
    setApiKeyState(value);
  }, []);

  const clearApiKey = useCallback(() => {
    sessionStorage.removeItem(apiSettings.STORAGE_KEY);
    setApiKeyState(null);
  }, []);

  const value = useMemo<ApiKeyContextValue>(
    () => ({ apiKey, setApiKey, clearApiKey }),
    [apiKey, clearApiKey, setApiKey],
  );

  return <ApiKeyContext.Provider value={value}>{children}</ApiKeyContext.Provider>;
};

