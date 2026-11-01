/** Shared types stub — expand in M1+. */
export type HealthStatus = { status: "ok" | "degraded" | "down" };

export type SessionToken = {
  access_token: string;
  token_type: "bearer";
  expires_in_minutes: number;
  subject: string;
};
