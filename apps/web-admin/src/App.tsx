import { useCallback, useEffect, useState } from "react";
import {
  API_BASE,
  getAudit,
  getOrgs,
  getStats,
  getSyncFailures,
  patchOrg,
  staffLogin,
} from "./api";
import "./App.css";

export default function App() {
  const [token, setToken] = useState<string | null>(null);
  const [stats, setStats] = useState<Record<string, number | string> | null>(null);
  const [orgs, setOrgs] = useState<
    {
      id: string;
      name: string;
      org_type: string;
      is_active: boolean;
      approval_status: string;
    }[]
  >([]);
  const [audit, setAudit] = useState<
    { id: string; actor: string; action: string; decision: string; created_at: string }[]
  >([]);
  const [failures, setFailures] = useState<
    { id: string; idempotency_key: string; error_message: string | null }[]
  >([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async (tok: string) => {
    const [s, o, a, f] = await Promise.all([
      getStats(tok),
      getOrgs(tok),
      getAudit(tok),
      getSyncFailures(tok),
    ]);
    setStats(s);
    setOrgs(o);
    setAudit(a);
    setFailures(f);
  }, []);

  useEffect(() => {
    (async () => {
      try {
        setBusy(true);
        const session = await staffLogin();
        setToken(session.access_token);
        await refresh(session.access_token);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setBusy(false);
      }
    })();
  }, [refresh]);

  async function setStatus(id: string, approval_status: string, is_active: boolean) {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      await patchOrg(token, id, {
        approval_status,
        is_active,
        note: "m5 admin stub",
      });
      await refresh(token);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="shell">
      <header>
        <p className="kicker">Platform admin</p>
        <h1>Universal Health QR</h1>
        <p>Aggregate ops only — no bulk clinical browsing. Synthetic demo.</p>
        <span className="chip">{API_BASE}</span>
      </header>

      {error && <p className="error">{error}</p>}
      {busy && <p className="muted">Loading…</p>}

      {stats && (
        <section className="stats">
          {(
            [
              ["Patients", stats.patients],
              ["Organizations", stats.organizations],
              ["Records", stats.clinical_records],
              ["Sync OK", stats.integration_confirmed],
              ["Sync failed", stats.integration_failed],
              ["Audit denials", stats.audit_denials],
            ] as const
          ).map(([label, value]) => (
            <article key={label}>
              <div className="muted">{label}</div>
              <strong>{String(value)}</strong>
            </article>
          ))}
        </section>
      )}

      <section className="panel">
        <h2>Organizations</h2>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Status</th>
              <th>Active</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {orgs.map((o) => (
              <tr key={o.id}>
                <td>{o.name}</td>
                <td>{o.org_type}</td>
                <td>{o.approval_status}</td>
                <td>{o.is_active ? "yes" : "no"}</td>
                <td className="actions">
                  <button
                    type="button"
                    onClick={() => setStatus(o.id, "approved", true)}
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    onClick={() => setStatus(o.id, "suspended", false)}
                  >
                    Suspend
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="panel">
        <h2>Failed sync events</h2>
        {failures.length === 0 ? (
          <p className="muted">None right now.</p>
        ) : (
          failures.map((f) => (
            <div key={f.id} className="row">
              <code>{f.idempotency_key}</code>
              <span className="muted">{f.error_message || "failed"}</span>
            </div>
          ))
        )}
      </section>

      <section className="panel">
        <h2>Recent audit</h2>
        {audit.map((a) => (
          <div key={a.id} className="row">
            <span>
              {a.action} · <em>{a.decision}</em>
            </span>
            <span className="muted">
              {a.actor} · {new Date(a.created_at).toLocaleString()}
            </span>
          </div>
        ))}
      </section>
    </div>
  );
}
