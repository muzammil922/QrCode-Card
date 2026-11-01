/**
 * Content script — allowlisted demo hospital origins only.
 * Page content is untrusted; we only read known data-* markers and fill approved fields after explicit confirmation from the side panel.
 */

(function () {
  function detectHospital() {
    const marker = document.body?.getAttribute("data-uhq-hospital");
    if (marker === "a" || marker === "b") return marker;
    const host = location.host;
    if (host.includes("5173")) return "a";
    if (host.includes("5174")) return "b";
    return null;
  }

  function readSyncStatus() {
    const el = document.querySelector("[data-uhq-sync-status]");
    return el ? el.getAttribute("data-uhq-sync-status") : null;
  }

  function reportContext() {
    const hospital = detectHospital();
    chrome.runtime.sendMessage({
      type: "UHQ_PAGE_CONTEXT",
      hospital,
      syncStatus: readSyncStatus(),
      origin: location.origin,
    });
  }

  function prefillDemographics(fields) {
    if (!fields || typeof fields !== "object") {
      return { ok: false, error: "No fields" };
    }
    const hospital = detectHospital();
    if (hospital !== "b") {
      return { ok: false, error: "Prefill only allowed on Hospital B demo" };
    }
    const allowed = ["display_name", "uhid", "date_of_birth"];
    const filled = [];
    for (const key of allowed) {
      if (fields[key] == null || fields[key] === "") continue;
      const input = document.querySelector(`[data-uhq-field="${key}"]`);
      if (input && "value" in input) {
        input.value = String(fields[key]);
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
        filled.push(key);
      }
    }
    return { ok: true, filled };
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type === "UHQ_DETECT") {
      sendResponse({
        ok: true,
        hospital: detectHospital(),
        syncStatus: readSyncStatus(),
        origin: location.origin,
      });
      return false;
    }
    if (message?.type === "UHQ_PREFILL") {
      sendResponse(prefillDemographics(message.fields));
      return false;
    }
    return false;
  });

  reportContext();
  const obs = new MutationObserver(() => reportContext());
  if (document.body) {
    obs.observe(document.body, {
      attributes: true,
      subtree: true,
      attributeFilter: ["data-uhq-sync-status", "data-uhq-hospital"],
    });
  }
})();
