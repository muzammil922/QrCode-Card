/** Shared types — M2 sync + session. */
export type HealthStatus = { status: "ok" | "degraded" | "down" };

export type SessionToken = {
  access_token: string;
  token_type: "bearer";
  expires_in_minutes: number;
  subject: string;
  org_id?: string | null;
  org_name?: string | null;
};

export type SyncStatus = "queued" | "sent" | "confirmed" | "failed";

export type SyncEventSummary = {
  id: string;
  status: SyncStatus;
  idempotency_key: string;
  retry_count: number;
  error_message?: string | null;
};
