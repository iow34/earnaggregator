const STATUS_COLORS: Record<string, string> = {
  running: "badge badge--green",
  queued: "badge badge--blue",
  scheduled: "badge badge--purple",
  pending_approval: "badge badge--amber",
  completed: "badge badge--gray",
  cancelled: "badge badge--red",
  failed: "badge badge--red",
};

export const StatusBadge = ({ status }: { status: string }) => {
  const normalized = status?.toLowerCase() ?? "unknown";
  const className = STATUS_COLORS[normalized] ?? "badge badge--gray";

  return <span className={className}>{normalized.replace("_", " ")}</span>;
};

