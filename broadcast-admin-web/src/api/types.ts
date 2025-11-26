export type BroadcastStatus =
  | "draft"
  | "pending_approval"
  | "queued"
  | "running"
  | "scheduled"
  | "completed"
  | "cancelled";

export interface AdminSummary {
  id: number;
  email: string;
  role: string;
}

export interface BroadcastStats {
  sent: number;
  failed: number;
  pending: number;
  skipped: number;
}

export interface BroadcastSummary {
  id: number;
  title: string;
  status: BroadcastStatus;
  channel: string;
  total_recipients: number;
  stats: BroadcastStats;
  requires_approval: boolean;
  scheduled_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  author: AdminSummary;
}

export interface PaginatedResponse<TItem> {
  items: TItem[];
  page: number;
  per_page: number;
  total: number;
}

export interface BroadcastContentPayload {
  text?: string;
  parse_mode?: "HTML" | "Markdown" | "MarkdownV2";
  media_file_id?: string | null;
  media_url?: string | null;
  buttons?: Array<{ text: string; url?: string }>;
  disable_link_preview?: boolean;
}

export interface BroadcastFiltersPayload {
  is_subscribed?: boolean;
  languages?: string[];
  tags_all?: string[];
  tags_any?: string[];
  telegram_ids?: number[];
  last_active_after?: string | null;
}

export interface BroadcastDetail {
  broadcast: BroadcastSummary;
  content: BroadcastContentPayload;
  filters: BroadcastFiltersPayload;
  metadata: Record<string, unknown>;
  preview_chat_id?: number | null;
  batch_size: number;
}

export interface DashboardMetrics {
  total_broadcasts: number;
  active_broadcasts: number;
  scheduled_broadcasts: number;
  pending_approval: number;
  sent_today: number;
  failed_today: number;
}

export interface BroadcastEvent {
  id: number;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
  admin?: AdminSummary | null;
}

export interface BroadcastRecipient {
  id: number;
  telegram_id: number;
  language: string;
  status: string;
  attempts: number;
  message_id?: string | null;
  error_code?: string | null;
  last_attempt_at?: string | null;
  created_at: string;
}

export interface CreateBroadcastPayload {
  title: string;
  content_type: "text" | "markdown" | "html";
  content: BroadcastContentPayload;
  filters: BroadcastFiltersPayload;
  channel?: string;
  requires_approval?: boolean;
  scheduled_at?: string | null;
  preview_chat_id?: number | null;
  batch_size?: number;
}

