import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { createBroadcast } from "../api/broadcasts";

export const CreateBroadcastPage = () => {
  const [title, setTitle] = useState("");
  const [message, setMessage] = useState("");
  const [languages, setLanguages] = useState("ua");
  const [telegramIds, setTelegramIds] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [requiresApproval, setRequiresApproval] = useState(false);
  const [successId, setSuccessId] = useState<number | null>(null);

  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: createBroadcast,
    onSuccess: (data) => {
      setSuccessId(data.broadcast_id);
      void queryClient.invalidateQueries({ queryKey: ["broadcasts"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    setSuccessId(null);

    const payload = {
      title,
      content_type: "text" as const,
      content: {
        text: message,
        parse_mode: "HTML" as const,
      },
      filters: {
        languages: languages
          .split(",")
          .map((lang) => lang.trim())
          .filter(Boolean),
        telegram_ids: telegramIds
          .split(",")
          .filter((id) => id.trim() !== "")
          .map((id) => Number(id.trim()))
          .filter((id) => Number.isSafeInteger(id) && id > 0),
      },
      requires_approval: requiresApproval,
      scheduled_at: scheduledAt ? new Date(scheduledAt).toISOString() : null,
    };

    mutation.mutate(payload);
  };

  return (
    <section className="page">
      <header>
        <h1>Create broadcast</h1>
        <p>Compose a text-based broadcast and choose the recipient segment.</p>
      </header>

      <form className="card form" onSubmit={handleSubmit}>
        <label>
          Title
          <input value={title} onChange={(event) => setTitle(event.target.value)} required />
        </label>

        <label>
          Message (HTML allowed)
          <textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            rows={6}
            required
          />
        </label>

        <label>
          Languages (comma separated)
          <input value={languages} onChange={(event) => setLanguages(event.target.value)} />
        </label>

        <label>
          Telegram IDs (optional, comma separated)
          <input value={telegramIds} onChange={(event) => setTelegramIds(event.target.value)} />
        </label>

        <label>
          Scheduled time
          <input
            type="datetime-local"
            value={scheduledAt}
            onChange={(event) => setScheduledAt(event.target.value)}
          />
        </label>

        <label className="checkbox">
          <input
            type="checkbox"
            checked={requiresApproval}
            onChange={(event) => setRequiresApproval(event.target.checked)}
          />
          Requires owner approval
        </label>

        <button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Submitting…" : "Create broadcast"}
        </button>

        {mutation.isError && (
          <p className="error">Failed to create broadcast: {(mutation.error as Error).message}</p>
        )}

        {successId && (
          <p className="success">
            Broadcast #{successId} created. Track progress in the broadcast list.
          </p>
        )}
      </form>
    </section>
  );
};

