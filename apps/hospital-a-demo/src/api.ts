const API_BASE = (
  import.meta.env.VITE_API_BASE || "https://codebase.flowlab.fun"
).replace(/\/$/, "");

export type Patient = {
  id: string;
  uhid: string;
  display_name: string;
  date_of_birth: string | null;
  is_synthetic: boolean;
  created_at: string;
};

export type SyncEvent = {
  id: string;
  status: "queued" | "sent" | "confirmed" | "failed";
  idempotency_key: string;
  retry_count: number;
  error_message: string | null;
  fhir_resource_id: string | null;
};

async function parseError(res: Response): Promise<string> {
  try {
    const j = await res.json();
    if (typeof j.detail === "string") return j.detail;
    return JSON.stringify(j.detail ?? j);
  } catch {
    return res.statusText;
  }
}

export async function createSession(
  username: string,
  password: string,
  orgName = "Demo Hospital A"
): Promise<{ access_token: string; org_id: string | null; org_name: string | null }> {
  const res = await fetch(`${API_BASE}/api/v1/auth/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, org_name: orgName }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function listPatients(token: string): Promise<Patient[]> {
  const res = await fetch(`${API_BASE}/api/v1/patients?limit=50`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function lookupPatient(
  token: string,
  uhid: string
): Promise<Patient | null> {
  const res = await fetch(
    `${API_BASE}/api/v1/patients?uhid=${encodeURIComponent(uhid)}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  if (!res.ok) throw new Error(await parseError(res));
  const rows: Patient[] = await res.json();
  return rows[0] ?? null;
}

export async function registerPatient(
  token: string,
  displayName: string
): Promise<Patient & { card?: { qr_token: string } }> {
  const res = await fetch(`${API_BASE}/api/v1/patients`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ display_name: displayName }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function submitIntegrationEvent(
  token: string,
  body: {
    patient_id: string;
    source_org_name: string;
    source_record_id: string;
    version: number;
    medication_text: string;
    dose_text: string;
    status: "final" | "approved";
    local_saved: boolean;
  }
): Promise<SyncEvent & { duplicate?: boolean }> {
  const res = await fetch(`${API_BASE}/api/v1/integration-events`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function getSyncEvent(
  token: string,
  eventId: string
): Promise<SyncEvent> {
  const res = await fetch(`${API_BASE}/api/v1/sync-events/${eventId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export { API_BASE };
