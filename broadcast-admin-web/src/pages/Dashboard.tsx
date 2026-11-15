import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { getDashboardMetrics, getDashboardRecentBroadcasts } from "../api/broadcasts";
import { StatusBadge } from "../components/ui/StatusBadge";
import { formatDate, formatNumber } from "../utils/format";

const METRIC_FIELDS = [
  { key: "total_broadcasts", label: "Total broadcasts" },
  { key: "active_broadcasts", label: "Active now" },
  { key: "scheduled_broadcasts", label: "Scheduled" },
  { key: "pending_approval", label: "Waiting approval" },
  { key: "sent_today", label: "Sent today" },
  { key: "failed_today", label: "Failed today" },
] as const;

export const DashboardPage = () => {
  const metricsQuery = useQuery({
    queryKey: ["dashboard", "metrics"],
    queryFn: getDashboardMetrics,
    refetchInterval: 10000,
  });

  const recentQuery = useQuery({
    queryKey: ["dashboard", "recent"],
    queryFn: getDashboardRecentBroadcasts,
    refetchInterval: 10000,
  });

  return (
    <section className="page">
      <header>
        <h1>Dashboard</h1>
        <p>Monitor the health of manual broadcasts in real time.</p>
      </header>

      {(metricsQuery.isError || recentQuery.isError) && <p role="alert" className="error">Could not refresh dashboard data. Check your API connection and administrator key.</p>}
      <div className="card-grid">
        {METRIC_FIELDS.map((metric) => (
          <article className="card" key={metric.key}>
            <p className="placeholder">{metric.label}</p>
            <h2>
              {metricsQuery.isError ? "—" : metricsQuery.isLoading
                ? "…"
                : formatNumber(metricsQuery.data?.[metric.key] ?? 0)}
            </h2>
          </article>
        ))}
      </div>

      <div className="card">
        <header className="page-header">
          <div>
            <h2>Recent broadcasts</h2>
            <p>Latest items across all channels.</p>
          </div>
          <Link className="primary-link" to="/broadcasts">
            View all
          </Link>
        </header>

        {recentQuery.isLoading ? (
          <p className="placeholder">Loading recent broadcasts…</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Status</th>
                <th>Recipients</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {recentQuery.data?.items.map((item) => (
                <tr key={item.id}>
                  <td>
                    <Link to={`/broadcasts/${item.id}`}>{item.title}</Link>
                  </td>
                  <td>
                    <StatusBadge status={item.status} />
                  </td>
                  <td>{formatNumber(item.total_recipients)}</td>
                  <td>{formatDate(item.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
};

