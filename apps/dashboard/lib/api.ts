const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`);
  }
  return res.json();
}

export interface ReviewSummary {
  id: string;
  status: string;
  trigger_type: string;
  verdict: string;
  final_summary: string | null;
  critical_count: number;
  warning_count: number;
  info_count: number;
  tokens_used: number;
  cost_usd: number;
  started_at: string | null;
  completed_at: string | null;
  pr: { number: number; title: string; author: string; head_sha: string } | null;
  repo: { full_name: string } | null;
}

export interface ReviewDetail extends ReviewSummary {
  issues: IssueItem[];
  senior_comments: SeniorCommentItem[];
}

export interface IssueItem {
  id: string;
  agent_type: string;
  severity: string;
  category: string;
  file_path: string;
  line_number: string | null;
  description: string;
  suggested_fix: string | null;
  generated_prompt: string | null;
}

export interface SeniorCommentItem {
  id: string;
  reviewer_login: string;
  body: string;
  file_path: string | null;
  guidance: string | null;
  generated_prompt: string | null;
}

export interface PromptItem {
  id: string;
  agent_type: string;
  severity: string;
  category: string;
  file_path: string;
  line_number: string | null;
  description: string;
  generated_prompt: string;
  repo: string;
  pr_number: number;
  created_at: string | null;
}

export interface NotificationItem {
  id: string;
  type: string;
  title: string;
  body: string;
  metadata: Record<string, unknown>;
  is_read: boolean;
  created_at: string | null;
}

export async function getReviews(page = 1, limit = 20) {
  return fetchAPI<{ total: number; page: number; limit: number; reviews: ReviewSummary[] }>(
    `/reviews?page=${page}&limit=${limit}`
  );
}

export async function getReview(id: string) {
  return fetchAPI<ReviewDetail>(`/reviews/${id}`);
}

export async function getPrompts(params: {
  page?: number;
  limit?: number;
  severity?: string;
  agent?: string;
  search?: string;
} = {}) {
  const query = new URLSearchParams();
  if (params.page) query.set("page", String(params.page));
  if (params.limit) query.set("limit", String(params.limit));
  if (params.severity) query.set("severity", params.severity);
  if (params.agent) query.set("agent", params.agent);
  if (params.search) query.set("search", params.search);
  return fetchAPI<{ total: number; page: number; limit: number; prompts: PromptItem[] }>(
    `/prompts?${query.toString()}`
  );
}

export async function getNotifications(page = 1, unreadOnly = false) {
  return fetchAPI<{ total: number; notifications: NotificationItem[] }>(
    `/notifications?page=${page}&unread_only=${unreadOnly}`
  );
}

export async function markNotificationRead(id: string) {
  return fetchAPI<{ status: string }>(`/notifications/${id}/read`, { method: "PATCH" });
}

export async function markAllNotificationsRead() {
  return fetchAPI<{ status: string }>("/notifications/mark-all-read", { method: "POST" });
}

export interface DashboardStats {
  total_reviews: number;
  total_issues: number;
  total_repos: number;
  total_prs: number;
  issues_by_severity: { critical: number; warning: number; info: number };
  total_cost_usd: number;
  total_tokens: number;
  recent_reviews: ReviewSummary[];
}

export async function getStats() {
  return fetchAPI<DashboardStats>("/reviews/stats");
}

export async function ratePrompt(issueId: string, helpful: boolean) {
  return fetchAPI<{ status: string; issue_id: string; helpful: boolean }>(
    `/prompts/${issueId}/feedback`,
    { method: "POST", body: JSON.stringify({ helpful }) }
  );
}
