import { type FormEvent, useState } from "react";

import { useApiKey } from "../../context/apiKey";

export const ApiKeyGate = ({ children }: { children: React.ReactNode }) => {
  const { apiKey, setApiKey } = useApiKey();
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (apiKey || import.meta.env.VITE_PREVIEW_MODE === "true") {
    return <>{children}</>;
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!value.trim()) {
      setError("API key is required");
      return;
    }
    setApiKey(value.trim());
    setValue("");
    setError(null);
  };

  return (
    <div className="api-key-gate">
      <form className="api-key-form" onSubmit={handleSubmit}>
        <h1>Broadcast Admin</h1>
        <p>Enter your administrator API key to continue.</p>
        <input
          type="password"
          aria-label="Administrator API key"
          autoComplete="off"
          placeholder="Administrator API key"
          value={value}
          onChange={(event) => setValue(event.target.value)}
        />
        {error && <span className="error">{error}</span>}
        <button type="submit">Unlock</button>
      </form>
    </div>
  );
};

