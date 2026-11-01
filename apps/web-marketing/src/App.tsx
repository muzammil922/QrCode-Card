import "./App.css";

const sections = [
  { id: "home", title: "One QR. Continuity of care." },
  { id: "how", title: "How it works" },
  { id: "security", title: "Security & privacy" },
  { id: "contact", title: "Contact" },
];

export default function App() {
  return (
    <div className="page">
      <nav>
        <strong>Universal Health QR</strong>
        <div className="links">
          {sections.map((s) => (
            <a key={s.id} href={`#${s.id}`}>
              {s.title.split(" ")[0]}
            </a>
          ))}
        </div>
      </nav>

      <header id="home" className="hero">
        <p className="eyebrow">For patients · hospitals · labs</p>
        <h1>One Universal Health ID across participating providers</h1>
        <p className="lede">
          Carry an opaque QR identity. Authorized staff see your permitted history —
          without replacing every hospital’s existing software.
        </p>
        <div className="cta">
          <a className="primary" href="https://codebase.flowlab.fun/docs">
            API docs
          </a>
          <a href="#how">See how it works</a>
        </div>
      </header>

      <section id="how">
        <h2>How it works</h2>
        <ol>
          <li>Patient registers and receives a Universal Health ID + QR (no PHI in the code).</li>
          <li>Hospital A saves a final prescription; a connector syncs to Universal Health Cloud.</li>
          <li>Hospital B authenticates, scans the same QR, and views authorized history in a side panel.</li>
        </ol>
      </section>

      <section id="security">
        <h2>Security & privacy</h2>
        <ul>
          <li>QR scan alone never grants access — backend authorizes every request.</li>
          <li>Consent-scoped reads, append-only audit, synthetic data in the prototype.</li>
          <li>Not a universal EHR scraper; adapters are hospital-specific.</li>
        </ul>
      </section>

      <section id="contact">
        <h2>Contact / partnership</h2>
        <p>
          Hospital partnership requests: email{" "}
          <a href="mailto:partnerships@flowlab.fun">partnerships@flowlab.fun</a>{" "}
          (placeholder for the prototype).
        </p>
        <p className="fine">
          Phase 1 demo stack — not a certified clinical system.
        </p>
      </section>

      <footer>Universal Health QR · prototype marketing shell</footer>
    </div>
  );
}
