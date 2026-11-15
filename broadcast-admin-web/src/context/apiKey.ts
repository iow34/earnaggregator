import { createContext, useContext } from "react";

export interface ApiKeyContextValue {
  apiKey: string | null;
  setApiKey: (value: string) => void;
  clearApiKey: () => void;
}

export const ApiKeyContext = createContext<ApiKeyContextValue | undefined>(undefined);

export const useApiKey = () => {
  const ctx = useContext(ApiKeyContext);
  if (!ctx) throw new Error("useApiKey must be used within ApiKeyProvider");
  return ctx;
};
