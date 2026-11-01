import { FormEvent, useEffect, useState } from "react";
import {
  API_BASE,
  createSession,
  getPatient,
  getRecords,
  lookupByUhid,
  Patient,
  PatientRecord,
  resolveQr,
} from "./api";

const DEMO_USER = import.meta.env.VITE_DEMO_USERNAME || "demo@health.local";
const DEMO_PASS =
  import.meta.env.VITE_DEMO_PASSWORD || "demo-password-change-me";

type Mode = "uhid" | "qr" | "id";

export default function App() {
  const [token, setToken] = useState<string | null>(null);
  const [orgId, setOrgId] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("uhid");
  const [query, setQuery] = useState("");
  const [patient, setPatient] = useState<Patient | null>(null);
  const [records, setRecords] = useState<PatientRecord[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setBusy(true);
        const session = await createSession(DEMO_USER, DEMO_PASS);
        if (cancelled) return;
        setToken(session.access_token);
        setOrgId(session.org_id);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setBusy(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!token || !query.trim()) return;
    setError(null);
    setBusy(true);
    setPatient(null);
    setRecords([]);
    try {
      let p: Patient | null = null;
      const q = query.trim();
      if (mode === "qr") {
        p = await resolveQr(token, q);
      } else if (mode === "id") {
        p = await getPatient(token, q);
      } else {
        p = await lookupByUhid(token, q);
        if (!p) throw new Error("No patient for that UHID");
      }
      setPatient(p);
      const page = await getRecords(token, p.id, orgId);
      setRecords(page.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="shell">
      <header className="masthead">
        <p className="kicker">Demo Hospital B</p>
        <h1>Ridge Clinic B</h1>
        <p>
          Chart intake — resolve a Universal Health QR patient and review synced
          prescriptions with provenance from Hospital A.
        </p>
        <span className="api-chip">{API_BASE}</span>
      </header>

      <section className="intake">
        <h2>Identify patient</h2>
        <div className="tabs">
          <button
            type="button"
            className={mode === "uhid" ? "active" : ""}
            onClick={() => setMode("uhid")}
          >
            UHID
          </button>
          <button
            type="button"
            className={mode === "qr" ? "active" : ""}
            onClick={() => setMode("qr")}
          >
            QR token
          </button>
          <button
            type="button"
            className={mode === "id" ? "active" : ""}
            onClick={() => setMode("id")}
          >
            Patient id
          </button>
        </div>

        <form onSubmit={onSubmit}>
          <label htmlFor="q">
            {mode === "uhid" && "Paste UHID"}
            {mode === "qr" && "Paste opaque QR token"}
            {mode === "id" && "Paste patient UUID"}
          </label>
          <input
            id="q"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={
              mode === "uhid" ? "UHQ-…" : mode === "qr" ? "opaque token…" : "uuid…"
            }
            autoComplete="off"
          />
          <button className="primary" type="submit" disabled={busy || !token}>
            {busy ? "Loading…" : "Load synced history"}
          </button>
        </form>

        {error && <p className="error">{error}</p>}

        {patient && (
          <div className="patient-banner">
            <strong>{patient.display_name}</strong>
            <code>{patient.uhid}</code>
          </div>
        )}

        {patient && (
          <div className="records">
            {records.length === 0 ? (
              <p className="empty">No synced clinical records yet for this patient.</p>
            ) : (
              records.map((r) => (
                <article key={r.id} className="record">
                  <div className="meta">
                    {r.resource_type} · v{r.version} ·{" "}
                    {r.source_org_name ?? "unknown source"} ·{" "}
                    {new Date(r.created_at).toLocaleString()}
                  </div>
                  <h3>
                    {r.body.medicationCodeableConcept?.text ?? "MedicationRequest"}
                  </h3>
                  <p>
                    {r.body.dosageInstruction?.[0]?.text ?? "—"}
                    {r.source_record_id
                      ? ` · source record ${r.source_record_id}`
                      : ""}
                  </p>
                </article>
              ))
            )}
          </div>
        )}
      </section>
    </div>
  );
}
