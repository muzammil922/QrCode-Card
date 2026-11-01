const API_BASE =
  import.meta.env.VITE_API_BASE || "https://codebase.flowlab.fun";

export { API_BASE };

async function parse(res: Response) {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail || res.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export async function staffLogin() {
  const res = await fetch(`${API_BASE}/api/v1/auth/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username: "demo@health.local",
      password: "demo-password-change-me",
    }),
  });
  return parse(res);
}

export async function getStats(token: string) {
  return parse(
    await fetch(`${API_BASE}/api/v1/admin/stats`, {
      headers: { Authorization: `Bearer ${token}` },
    })
  );
}

export async function getOrgs(token: string) {
  return parse(
    await fetch(`${API_BASE}/api/v1/admin/organizations`, {
      headers: { Authorization: `Bearer ${token}` },
    })
  );
}

export async function patchOrg(
  token: string,
  id: string,
  body: { approval_status: string; is_active: boolean; note?: string }
) {
  return parse(
    await fetch(`${API_BASE}/api/v1/admin/organizations/${id}`, {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    })
  );
}

export async function getAudit(token: string) {
  return parse(
    await fetch(`${API_BASE}/api/v1/audit-events?limit=40`, {
      headers: { Authorization: `Bearer ${token}` },
    })
  );
}

export async function getSyncFailures(token: string) {
  return parse(
    await fetch(`${API_BASE}/api/v1/admin/sync-failures`, {
      headers: { Authorization: `Bearer ${token}` },
    })
  );
}
