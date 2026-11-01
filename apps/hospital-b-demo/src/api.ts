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

export type PatientRecord = {
  id: string;
  resource_type: string;
  version: number;
  status: string;
  source_org_id: string | null;
  source_org_name: string | null;
  source_record_id: string | null;
  body: {
    medicationCodeableConcept?: { text?: string };
    dosageInstruction?: { text?: string }[];
    authoredOn?: string;
    meta?: { source?: string };
  };
  created_at: string;
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
  orgName = "Demo Hospital B"
): Promise<{ access_token: string; org_id: string | null }> {
  const res = await fetch(`${API_BASE}/api/v1/auth/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, org_name: orgName }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function resolveQr(token: string, qrToken: string): Promise<Patient> {
  const res = await fetch(
    `${API_BASE}/api/v1/patients/resolve-qr?token=${encodeURIComponent(qrToken)}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function lookupByUhid(
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

export async function getPatient(token: string, id: string): Promise<Patient> {
  const res = await fetch(`${API_BASE}/api/v1/patients/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function getRecords(
  token: string,
  patientId: string,
  orgId?: string | null
): Promise<{ total: number; items: PatientRecord[] }> {
  const qs = orgId ? `?org_id=${encodeURIComponent(orgId)}` : "";
  const res = await fetch(
    `${API_BASE}/api/v1/patients/${patientId}/records${qs}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export { API_BASE };
