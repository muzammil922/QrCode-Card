import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  API_BASE,
  createSession,
  getSyncEvent,
  listPatients,
  lookupPatient,
  Patient,
  registerPatient,
  submitIntegrationEvent,
  SyncEvent,
} from "./api";

const DEMO_USER = import.meta.env.VITE_DEMO_USERNAME || "demo@health.local";
const DEMO_PASS =
  import.meta.env.VITE_DEMO_PASSWORD || "demo-password-change-me";

function newRecordId(): string {
  return `rx-a-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
}

export default function App() {
  const [token, setToken] = useState<string | null>(null);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selected, setSelected] = useState<Patient | null>(null);
  const [uhidLookup, setUhidLookup] = useState("");
  const [newName, setNewName] = useState("Synthetic Patient Alpha");
  const [medication, setMedication] = useState("Amoxicillin 500mg capsules");
  const [dose, setDose] = useState("1 capsule by mouth twice daily for 7 days");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [localNote, setLocalNote] = useState<string | null>(null);
  const [sync, setSync] = useState<SyncEvent | null>(null);
  const [lastRecordId, setLastRecordId] = useState<string | null>(null);

  const refreshPatients = useCallback(async (tok: string) => {
    const rows = await listPatients(tok);
    setPatients(rows);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setBusy(true);
        const session = await createSession(DEMO_USER, DEMO_PASS);
        if (cancelled) return;
        setToken(session.access_token);
        await refreshPatients(session.access_token);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setBusy(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshPatients]);

  useEffect(() => {
    if (!token || !sync || sync.status === "confirmed" || sync.status === "failed") {
      return;
    }
    const id = sync.id;
    const timer = window.setInterval(async () => {
      try {
        const next = await getSyncEvent(token, id);
        setSync(next);
      } catch {
        /* keep last known */
      }
    }, 1200);
    return () => window.clearInterval(timer);
  }, [token, sync]);

  async function onLookup(e: FormEvent) {
    e.preventDefault();
    if (!token || !uhidLookup.trim()) return;
    setError(null);
    setBusy(true);
    try {
      const p = await lookupPatient(token, uhidLookup.trim());
      if (!p) throw new Error("No patient for that UHID");
      setSelected(p);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function onRegister(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setError(null);
    setBusy(true);
    try {
      const p = await registerPatient(token, newName.trim());
      await refreshPatients(token);
      setSelected({
        id: p.id,
        uhid: p.uhid,
        display_name: p.display_name,
        date_of_birth: null,
        is_synthetic: p.is_synthetic,
        created_at: new Date().toISOString(),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function onSavePrescription(e: FormEvent) {
    e.preventDefault();
    if (!token || !selected) return;
    setError(null);
    setSync(null);
    setBusy(true);
    const recordId = newRecordId();
    try {
      // Local EHR save (demo): succeed before any cloud call
      await new Promise((r) => setTimeout(r, 350));
      setLocalNote(`Local chart saved · ${recordId}`);
      setLastRecordId(recordId);

      const event = await submitIntegrationEvent(token, {
        patient_id: selected.id,
        source_org_name: "Demo Hospital A",
        source_record_id: recordId,
        version: 1,
        medication_text: medication.trim(),
        dose_text: dose.trim(),
        status: "final",
        local_saved: true,
      });
      setSync(event);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app">
      <header className="brand-bar">
        <div>
          <h1>Harborview A</h1>
          <p>
            Prescription desk · Demo Hospital A · cloud sync only after final save
          </p>
        </div>
        <span className="badge">API {API_BASE}</span>
      </header>

      <div className="layout">
        <section className="panel">
          <h2>Patients</h2>
          <form onSubmit={onLookup} className="row" style={{ marginBottom: "0.75rem" }}>
            <div style={{ flex: 1, minWidth: "12rem" }}>
              <label htmlFor="uhid">Lookup UHID</label>
              <input
                id="uhid"
                value={uhidLookup}
                onChange={(e) => setUhidLookup(e.target.value)}
                placeholder="UHQ-…"
              />
            </div>
            <button type="submit" disabled={busy} style={{ alignSelf: "end" }}>
              Resolve
            </button>
          </form>

          <form onSubmit={onRegister}>
            <label htmlFor="newName">Register synthetic patient</label>
            <input
              id="newName"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
            <button type="submit" className="ghost" disabled={busy}>
              Register & select
            </button>
          </form>

          <p className="muted" style={{ marginTop: "1rem" }}>
            Recent synthetic patients
          </p>
          <ul className="patient-list">
            {patients.map((p) => (
              <li
                key={p.id}
                className={selected?.id === p.id ? "selected" : ""}
                onClick={() => setSelected(p)}
              >
                <strong>{p.display_name}</strong>
                <span>{p.uhid}</span>
              </li>
            ))}
            {patients.length === 0 && (
              <li>
                <strong>No patients yet</strong>
                <span>Register one to begin</span>
              </li>
            )}
          </ul>
        </section>

        <section className="panel">
          <h2>Final prescription</h2>
          {selected ? (
            <p className="muted">
              Selected: <strong>{selected.display_name}</strong> · {selected.uhid}
            </p>
          ) : (
            <p className="muted">Select or register a patient first.</p>
          )}

          <form onSubmit={onSavePrescription}>
            <label htmlFor="med">Medication (source text)</label>
            <input
              id="med"
              value={medication}
              onChange={(e) => setMedication(e.target.value)}
              required
            />
            <label htmlFor="dose">Dose / directions (source text)</label>
            <textarea
              id="dose"
              rows={3}
              value={dose}
              onChange={(e) => setDose(e.target.value)}
              required
            />
            <button type="submit" disabled={busy || !selected}>
              Save final & sync to cloud
            </button>
          </form>

          {localNote && <p className="muted">{localNote}</p>}
          {lastRecordId && (
            <p className="muted">Source record id: {lastRecordId}</p>
          )}

          {sync && (
            <div className="sync-status" data-status={sync.status}>
              <strong>Sync: {sync.status}</strong>
              <div className="muted">Event {sync.id}</div>
              {sync.fhir_resource_id && (
                <div className="muted">FHIR {sync.fhir_resource_id}</div>
              )}
              {sync.error_message && <div className="error">{sync.error_message}</div>}
            </div>
          )}
        </section>
      </div>

      {error && <p className="error">{error}</p>}
    </div>
  );
}
