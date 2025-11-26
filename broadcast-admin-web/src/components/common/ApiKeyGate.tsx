import { type FormEvent, useState } from "react";

import { useApiKey } from "../../context/ApiKeyContext";

export const ApiKeyGate = ({ children }: { children: React.ReactNode }) => {
  const { apiKey, setApiKey } = useApiKey();
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (apiKey) {
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
        <p>Enter the API key issued in the backend `.env` to continue.</p>
        <input
          type="password"
          placeholder="x-admin-api-key"
          value={value}
          onChange={(event) => setValue(event.target.value)}
        />
        {error && <span className="error">{error}</span>}
        <button type="submit">Unlock</button>
      </form>
    </div>
  );
};

