import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { QRCodeSVG } from "qrcode.react";
import {
  API_BASE,
  fetchCard,
  fetchRecords,
  loginPatient,
  registerPatient,
} from "./api";
import type { PatientAuth, RecordItem } from "./api";
import "./App.css";

type Mode = "login" | "register";

export default function App() {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("synthetic.you@example.com");
  const [password, setPassword] = useState("synthet1c-pass");
  const [displayName, setDisplayName] = useState("Synthetic You");
  const [session, setSession] = useState<PatientAuth | null>(null);
  const [qrToken, setQrToken] = useState<string | null>(null);
  const [records, setRecords] = useState<RecordItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const raw = localStorage.getItem("uhq_patient_session");
    if (!raw) return;
    try {
      const parsed = JSON.parse(raw) as PatientAuth;
      setSession(parsed);
      setQrToken(parsed.qr_token);
    } catch {
      localStorage.removeItem("uhq_patient_session");
    }
  }, []);

  useEffect(() => {
    if (!session) return;
    let cancelled = false;
    (async () => {
      try {
        const page = await fetchRecords(session.access_token);
        if (!cancelled) setRecords(page.items || []);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [session]);

  async function onAuth(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const auth =
        mode === "register"
          ? await registerPatient({
              email,
              password,
              display_name: displayName,
            })
          : await loginPatient({ email, password });
      setSession(auth);
      setQrToken(auth.qr_token);
      localStorage.setItem("uhq_patient_session", JSON.stringify(auth));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function refreshCard() {
    if (!session) return;
    setBusy(true);
    setError(null);
    try {
      const card = await fetchCard(session.access_token);
      setQrToken(card.qr_token);
      const next = { ...session, qr_token: card.qr_token, uhid: card.uhid };
      setSession(next);
      localStorage.setItem("uhq_patient_session", JSON.stringify(next));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  function logout() {
    setSession(null);
    setQrToken(null);
    setRecords([]);
    localStorage.removeItem("uhq_patient_session");
  }

  if (!session) {
    return (
      <div className="shell">
        <header>
          <p className="kicker">Universal Health QR</p>
          <h1>Patient portal</h1>
          <p>Synthetic accounts only. Demo OTP is always <code>123456</code>.</p>
          <span className="chip">{API_BASE}</span>
        </header>
        <section className="panel">
          <div className="tabs">
            <button
              type="button"
              className={mode === "login" ? "on" : ""}
              onClick={() => setMode("login")}
            >
              Login
            </button>
            <button
              type="button"
              className={mode === "register" ? "on" : ""}
              onClick={() => setMode("register")}
            >
              Register
            </button>
          </div>
          <form onSubmit={onAuth}>
            {mode === "register" && (
              <>
                <label htmlFor="name">Display name</label>
                <input
                  id="name"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  required
                />
              </>
            )}
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
            />
            <button className="primary" type="submit" disabled={busy}>
              {busy ? "Please wait…" : mode === "register" ? "Create account" : "Sign in"}
            </button>
          </form>
          {error && <p className="error">{error}</p>}
        </section>
      </div>
    );
  }

  return (
    <div className="shell">
      <header className="row">
        <div>
          <p className="kicker">Digital health card</p>
          <h1>{session.display_name}</h1>
          <p className="mono">{session.uhid}</p>
        </div>
        <button type="button" className="ghost" onClick={logout}>
          Log out
        </button>
      </header>

      <section className="card-grid">
        <article className="panel card-face">
          <h2>Show this QR at the hospital</h2>
          <p className="muted">Opaque token only — no medical data inside the code.</p>
          {qrToken ? (
            <div className="qr-wrap">
              <QRCodeSVG value={qrToken} size={200} level="M" includeMargin />
            </div>
          ) : (
            <p>No QR yet</p>
          )}
          <button type="button" className="primary" onClick={refreshCard} disabled={busy}>
            Rotate / refresh QR
          </button>
        </article>

        <article className="panel">
          <h2>Your synced prescriptions</h2>
          {records.length === 0 ? (
            <p className="muted">
              No records yet. After Hospital A saves a final prescription, it appears
              here.
            </p>
          ) : (
            records.map((r) => (
              <div key={r.id} className="rx">
                <div className="muted">
                  {r.source_org_name || "source?"} ·{" "}
                  {new Date(r.created_at).toLocaleString()}
                </div>
                <strong>
                  {r.body.medicationCodeableConcept?.text || r.resource_type}
                </strong>
                <p>{r.body.dosageInstruction?.[0]?.text || "—"}</p>
              </div>
            ))
          )}
          {error && <p className="error">{error}</p>}
        </article>
      </section>
    </div>
  );
}
