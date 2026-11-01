/* Universal Health QR — MV3 service worker (no long-lived secrets beyond chrome.storage). */

const DEFAULT_API = "https://codebase.flowlab.fun";

chrome.runtime.onInstalled.addListener(() => {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {});
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message || typeof message !== "object") {
    sendResponse({ ok: false, error: "Invalid message" });
    return false;
  }

  (async () => {
    try {
      if (message.type === "UHQ_GET_CONFIG") {
        const cfg = await chrome.storage.local.get([
          "apiBase",
          "accessToken",
          "subject",
          "orgId",
          "orgName",
        ]);
        sendResponse({
          ok: true,
          apiBase: cfg.apiBase || DEFAULT_API,
          loggedIn: Boolean(cfg.accessToken),
          subject: cfg.subject || null,
          orgId: cfg.orgId || null,
          orgName: cfg.orgName || null,
        });
        return;
      }

      if (message.type === "UHQ_LOGIN") {
        const apiBase = (message.apiBase || DEFAULT_API).replace(/\/$/, "");
        const res = await fetch(`${apiBase}/api/v1/auth/session`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            username: message.username,
            password: message.password,
            org_name: message.orgName || "Demo Hospital B",
          }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          throw new Error(data.detail || `Login failed (${res.status})`);
        }
        await chrome.storage.local.set({
          apiBase,
          accessToken: data.access_token,
          subject: data.subject || message.username,
          orgId: data.org_id || null,
          orgName: data.org_name || message.orgName || null,
        });
        sendResponse({ ok: true, subject: data.subject, orgId: data.org_id });
        return;
      }

      if (message.type === "UHQ_LOGOUT") {
        await chrome.storage.local.remove([
          "accessToken",
          "subject",
          "orgId",
          "orgName",
        ]);
        sendResponse({ ok: true });
        return;
      }

      if (message.type === "UHQ_API") {
        const cfg = await chrome.storage.local.get(["apiBase", "accessToken"]);
        const apiBase = (cfg.apiBase || DEFAULT_API).replace(/\/$/, "");
        if (!cfg.accessToken) {
          throw new Error("Not logged in");
        }
        const path = message.path.startsWith("/") ? message.path : `/${message.path}`;
        const res = await fetch(`${apiBase}${path}`, {
          method: message.method || "GET",
          headers: {
            Authorization: `Bearer ${cfg.accessToken}`,
            ...(message.body ? { "Content-Type": "application/json" } : {}),
          },
          body: message.body ? JSON.stringify(message.body) : undefined,
        });
        const text = await res.text();
        let data = null;
        try {
          data = text ? JSON.parse(text) : null;
        } catch {
          data = { raw: text };
        }
        if (!res.ok) {
          const detail =
            (data && (data.detail || data.message)) || `HTTP ${res.status}`;
          throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
        }
        sendResponse({ ok: true, data });
        return;
      }

      if (message.type === "UHQ_PAGE_CONTEXT") {
        // Forwarded from content script — store last known hospital page context
        await chrome.storage.local.set({
          lastHospital: message.hospital || null,
          lastSyncStatus: message.syncStatus || null,
        });
        sendResponse({ ok: true });
        return;
      }

      sendResponse({ ok: false, error: `Unknown type ${message.type}` });
    } catch (err) {
      sendResponse({
        ok: false,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  })();

  return true; // async
});
