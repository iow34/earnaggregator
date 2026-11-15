import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { getBroadcastDetail } from "../api/broadcasts";
import { StatusBadge } from "../components/ui/StatusBadge";
import { formatDate, formatNumber } from "../utils/format";

export const BroadcastDetailPage = () => {
  const { id } = useParams();

  const detailQuery = useQuery({
    queryKey: ["broadcast-detail", id],
    enabled: Boolean(id),
    queryFn: () => getBroadcastDetail(id!),
    refetchInterval: (query) => {
      const status = query.state.data?.broadcast.status;
      if (!status) return 7000;
      return ["completed", "cancelled"].includes(status) ? false : 7000;
    },
  });

  const detail = detailQuery.data;
  const stats = detail?.broadcast.stats;

  return (
    <section className="page">
      <header>
        <h1>{detail ? detail.broadcast.title : `Broadcast #${id}`}</h1>
        <p>Inspect configuration, content and high-level delivery stats.</p>
      </header>

      {detailQuery.isError && <p role="alert" className="error">Could not load this broadcast. Check its ID and your API connection.</p>}
      {detailQuery.isLoading && <div className="card placeholder">Loading broadcast…</div>}

      {detail && (
        <>
          <div className="card">
            <div className="page-header">
              <div>
                <h2>Status</h2>
                <StatusBadge status={detail.broadcast.status} />
              </div>
              <span>Created {formatDate(detail.broadcast.created_at)}</span>
            </div>
            <ul>
              <li>Total recipients: {formatNumber(detail.broadcast.total_recipients)}</li>
              <li>Batch size: {detail.batch_size}</li>
              <li>Scheduled: {formatDate(detail.broadcast.scheduled_at)}</li>
              <li>Started: {formatDate(detail.broadcast.started_at)}</li>
              <li>Completed: {formatDate(detail.broadcast.completed_at)}</li>
            </ul>
          </div>

          <div className="card-grid">
            <article className="card">
              <h3>Sent</h3>
              <strong>{formatNumber(stats?.sent ?? 0)}</strong>
            </article>
            <article className="card">
              <h3>Failed</h3>
              <strong>{formatNumber(stats?.failed ?? 0)}</strong>
            </article>
            <article className="card">
              <h3>Pending</h3>
              <strong>{formatNumber(stats?.pending ?? 0)}</strong>
            </article>
          </div>

          <div className="card">
            <h2>Content preview</h2>
            <p>{detail.content.text}</p>
          </div>
        </>
      )}
    </section>
  );
};

