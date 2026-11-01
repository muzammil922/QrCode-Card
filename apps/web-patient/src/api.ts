const API_BASE =
  import.meta.env.VITE_API_BASE || "https://codebase.flowlab.fun";

export { API_BASE };

async function parse(res: Response) {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail || data.message || res.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export type PatientAuth = {
  access_token: string;
  patient_id: string;
  uhid: string;
  display_name: string;
  qr_token: string;
  subject: string;
};

export type RecordItem = {
  id: string;
  resource_type: string;
  source_org_name: string | null;
  body: {
    medicationCodeableConcept?: { text?: string };
    dosageInstruction?: { text?: string }[];
  };
  created_at: string;
};

export async function registerPatient(input: {
  email: string;
  password: string;
  display_name: string;
  date_of_birth?: string;
  otp?: string;
}): Promise<PatientAuth> {
  const res = await fetch(`${API_BASE}/api/v1/auth/patient/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ otp: "123456", ...input }),
  });
  return parse(res);
}

export async function loginPatient(input: {
  email: string;
  password: string;
  otp?: string;
}): Promise<PatientAuth> {
  const res = await fetch(`${API_BASE}/api/v1/auth/patient/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ otp: "123456", ...input }),
  });
  return parse(res);
}

export async function fetchCard(token: string) {
  const res = await fetch(`${API_BASE}/api/v1/patients/me/card`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return parse(res);
}

export async function fetchRecords(token: string) {
  const res = await fetch(`${API_BASE}/api/v1/patients/me/records`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return parse(res);
}
