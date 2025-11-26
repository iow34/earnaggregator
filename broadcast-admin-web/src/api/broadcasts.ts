import { apiClient } from "./client";
import type {
  BroadcastDetail,
  BroadcastSummary,
  CreateBroadcastPayload,
  DashboardMetrics,
  PaginatedResponse,
} from "./types";

export interface BroadcastListParams {
  status?: string;
  page?: number;
  per_page?: number;
  search?: string;
}

export const getBroadcasts = async (params: BroadcastListParams) => {
  const { data } = await apiClient.get<PaginatedResponse<BroadcastSummary>>("/broadcasts", {
    params: {
      page: params.page ?? 1,
      per_page: params.per_page ?? 20,
      status: params.status || undefined,
      search: params.search || undefined,
      sort_by: "created_at",
    },
  });
  return data;
};

export const getDashboardMetrics = async () => {
  const { data } = await apiClient.get<DashboardMetrics>("/broadcasts/metrics/summary");
  return data;
};

export const getDashboardRecentBroadcasts = async () => {
  return getBroadcasts({ per_page: 5 });
};

export const getBroadcastDetail = async (broadcastId: number | string) => {
  const { data } = await apiClient.get<BroadcastDetail>(`/broadcasts/${broadcastId}`);
  return data;
};

export const createBroadcast = async (payload: CreateBroadcastPayload) => {
  const { data } = await apiClient.post<{ broadcast_id: number; status: string }>(
    "/broadcasts",
    payload,
  );
  return data;
};

