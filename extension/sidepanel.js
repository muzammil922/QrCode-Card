const $ = (id) => document.getElementById(id);

let currentPatient = null;
let scanTimer = null;
let mediaStream = null;

function show(el, on) {
  el.hidden = !on;
  if (on) el.classList.remove("hidden");
  else el.classList.add("hidden");
}

function setError(id, msg) {
  const el = $(id);
  if (!msg) {
    el.hidden = true;
    el.textContent = "";
    return;
  }
  el.hidden = false;
  el.textContent = msg;
}

function send(msg) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(msg, (response) => {
      if (chrome.runtime.lastError) {
        resolve({ ok: false, error: chrome.runtime.lastError.message });
        return;
      }
      resolve(response || { ok: false, error: "No response" });
    });
  });
}

async function api(path, method = "GET", body) {
  const res = await send({ type: "UHQ_API", path, method, body });
  if (!res.ok) throw new Error(res.error || "API error");
  return res.data;
}

async function refreshPageContext() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) {
    $("page-ctx").textContent = "Page: (no active tab)";
    $("sync-status").textContent = "—";
    return;
  }
  try {
    const ctx = await chrome.tabs.sendMessage(tab.id, { type: "UHQ_DETECT" });
    if (ctx?.ok) {
      $("page-ctx").textContent = `Page: Hospital ${String(ctx.hospital || "?").toUpperCase()} · ${ctx.origin}`;
      $("sync-status").textContent = ctx.syncStatus || "—";
    } else {
      $("page-ctx").textContent = "Page: open Hospital A (:5173) or B (:5174)";
      $("sync-status").textContent = "—";
    }
  } catch {
    $("page-ctx").textContent = "Page: content script not on this tab";
    $("sync-status").textContent = "—";
  }
}

async function boot() {
  const cfg = await send({ type: "UHQ_GET_CONFIG" });
  if (cfg.apiBase) $("apiBase").value = cfg.apiBase;
  if (cfg.loggedIn) {
    $("login-view").classList.add("hidden");
    $("main-view").classList.remove("hidden");
    $("who").textContent = `${cfg.subject || "staff"} · ${cfg.orgName || "org"}`;
    await refreshPageContext();
  }
}

$("btn-login").addEventListener("click", async () => {
  setError("login-error", "");
  $("btn-login").disabled = true;
  try {
    const res = await send({
      type: "UHQ_LOGIN",
      apiBase: $("apiBase").value.trim(),
      username: $("username").value.trim(),
      password: $("password").value,
      orgName: $("orgName").value,
    });
    if (!res.ok) throw new Error(res.error);
    $("login-view").classList.add("hidden");
    $("main-view").classList.remove("hidden");
    $("who").textContent = `${$("username").value.trim()} · ${$("orgName").value}`;
    await refreshPageContext();
  } catch (e) {
    setError("login-error", e.message || String(e));
  } finally {
    $("btn-login").disabled = false;
  }
});

$("btn-logout").addEventListener("click", async () => {
  stopScan();
  await send({ type: "UHQ_LOGOUT" });
  currentPatient = null;
  $("main-view").classList.add("hidden");
  $("login-view").classList.remove("hidden");
  $("patient-card").classList.add("hidden");
  $("records-card").classList.add("hidden");
});

$("btn-resolve").addEventListener("click", async () => {
  setError("main-error", "");
  const token = $("qrToken").value.trim();
  if (token.length < 8) {
    setError("main-error", "Paste a valid opaque QR token");
    return;
  }
  $("btn-resolve").disabled = true;
  try {
    const patient = await api(
      `/api/v1/patients/resolve-qr?token=${encodeURIComponent(token)}`
    );
    currentPatient = patient;
    $("p-name").textContent = patient.display_name;
    $("p-uhid").textContent = patient.uhid;
    $("p-meta").textContent = `synthetic=${patient.is_synthetic} · id=${patient.id}`;
    $("patient-card").classList.remove("hidden");

    const records = await api(`/api/v1/patients/${patient.id}/records`);
    const box = $("records");
    box.innerHTML = "";
    const items = records.items || [];
    if (!items.length) {
      box.innerHTML = `<p class="muted">No authorized clinical records yet.</p>`;
    } else {
      for (const r of items) {
        const med = r.body?.medicationCodeableConcept?.text || r.resource_type;
        const dose = r.body?.dosageInstruction?.[0]?.text || "";
        const el = document.createElement("article");
        el.className = "record";
        el.innerHTML = `<div class="muted">${r.resource_type} · ${r.source_org_name || "source?"} · ${new Date(r.created_at).toLocaleString()}</div>
          <h3>${escapeHtml(med)}</h3>
          <p class="muted">${escapeHtml(dose)}</p>`;
        box.appendChild(el);
      }
    }
    $("records-card").classList.remove("hidden");
    await refreshPageContext();
  } catch (e) {
    setError("main-error", e.message || String(e));
    currentPatient = null;
    $("patient-card").classList.add("hidden");
    $("records-card").classList.add("hidden");
  } finally {
    $("btn-resolve").disabled = false;
  }
});

$("btn-prefill").addEventListener("click", async () => {
  if (!currentPatient) return;
  const ok = window.confirm(
    `Prefill Hospital B demographics with:\n${currentPatient.display_name}\n${currentPatient.uhid}\n\nOnly approved fields. Continue?`
  );
  if (!ok) return;
  setError("main-error", "");
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) {
    setError("main-error", "No active tab");
    return;
  }
  try {
    const res = await chrome.tabs.sendMessage(tab.id, {
      type: "UHQ_PREFILL",
      fields: {
        display_name: currentPatient.display_name,
        uhid: currentPatient.uhid,
        date_of_birth: currentPatient.date_of_birth || "",
      },
    });
    if (!res?.ok) {
      throw new Error(res?.error || "Prefill failed — open Hospital B demo tab");
    }
    setError("main-error", "");
    alert(`Prefill applied: ${(res.filled || []).join(", ") || "no fields found"}`);
  } catch (e) {
    setError(
      "main-error",
      e.message || "Open http://localhost:5174 (Hospital B) and try again"
    );
  }
});

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function stopScan() {
  if (scanTimer) {
    clearInterval(scanTimer);
    scanTimer = null;
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach((t) => t.stop());
    mediaStream = null;
  }
  $("scanner").classList.add("hidden");
  $("scan-hint").classList.add("hidden");
}

$("btn-scan").addEventListener("click", async () => {
  setError("main-error", "");
  if (mediaStream) {
    stopScan();
    $("btn-scan").textContent = "Camera scan";
    return;
  }
  if (!("BarcodeDetector" in window)) {
    setError(
      "main-error",
      "Camera QR decode not available in this browser — paste the opaque token instead."
    );
    return;
  }
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment" },
      audio: false,
    });
    const video = $("scanner");
    video.srcObject = mediaStream;
    video.classList.remove("hidden");
    $("scan-hint").classList.remove("hidden");
    await video.play();
    $("btn-scan").textContent = "Stop camera";
    const detector = new BarcodeDetector({ formats: ["qr_code"] });
    scanTimer = setInterval(async () => {
      try {
        if (video.readyState < 2) return;
        const codes = await detector.detect(video);
        if (codes.length) {
          const raw = codes[0].rawValue;
          if (raw) {
            $("qrToken").value = raw;
            stopScan();
            $("btn-scan").textContent = "Camera scan";
            $("btn-resolve").click();
          }
        }
      } catch {
        /* keep scanning */
      }
    }, 500);
  } catch (e) {
    stopScan();
    setError("main-error", e.message || "Camera permission denied");
    $("btn-scan").textContent = "Camera scan";
  }
});

boot();
setInterval(() => {
  if (!$("main-view").classList.contains("hidden")) refreshPageContext();
}, 2500);
