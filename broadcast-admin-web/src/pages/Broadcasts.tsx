import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { getBroadcasts } from "../api/broadcasts";
import { StatusBadge } from "../components/ui/StatusBadge";
import { formatDate, formatNumber } from "../utils/format";

const STATUS_OPTIONS = [
  { value: "all", label: "All statuses" },
  { value: "running", label: "Running" },
  { value: "queued", label: "Queued" },
  { value: "scheduled", label: "Scheduled" },
  { value: "pending_approval", label: "Pending approval" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
];

export const BroadcastsPage = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const status = searchParams.get("status") ?? "all";
  const page = Number(searchParams.get("page") ?? "1");

  const query = useQuery({
    queryKey: ["broadcasts", status, page],
    queryFn: () =>
      getBroadcasts({
        status: status === "all" ? undefined : status,
        page,
      }),
    refetchInterval: 8000,
  });

  const totalPages = useMemo(() => {
    if (!query.data) return 1;
    return Math.max(1, Math.ceil(query.data.total / query.data.per_page));
  }, [query.data]);

  const updateParam = (nextStatus: string, nextPage = 1) => {
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev);
      params.set("status", nextStatus);
      params.set("page", String(nextPage));
      return params;
    });
  };

  const changePage = (direction: 1 | -1) => {
    const nextPage = Math.min(Math.max(1, page + direction), totalPages);
    updateParam(status, nextPage);
  };

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <h1>Broadcasts</h1>
          <p>Inspect the manual sends created by operators.</p>
        </div>
        <Link className="primary-link" to="/broadcasts/create">
          New broadcast
        </Link>
      </header>

      <div className="card">
        <div className="filters">
          <label>
            Status
            <select
              value={status}
              onChange={(event) => updateParam(event.target.value)}
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <button type="button" onClick={() => query.refetch()}>
            Refresh
          </button>
        </div>

        {query.isLoading ? (
          <p className="placeholder">Loading broadcasts…</p>
        ) : (
          <>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Status</th>
                  <th>Recipients</th>
                  <th>Updated</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {query.data?.items.map((item) => (
                  <tr key={item.id}>
                    <td>{item.title}</td>
                    <td>
                      <StatusBadge status={item.status} />
                    </td>
                    <td>{formatNumber(item.total_recipients)}</td>
                    <td>{formatDate(item.updated_at)}</td>
                    <td>
                      <Link to={`/broadcasts/${item.id}`}>Open</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="pagination">
              <button disabled={page <= 1} onClick={() => changePage(-1)}>
                Previous
              </button>
              <span>
                Page {page} / {totalPages}
              </span>
              <button disabled={page >= totalPages} onClick={() => changePage(1)}>
                Next
              </button>
            </div>
          </>
        )}
      </div>
    </section>
  );
};

