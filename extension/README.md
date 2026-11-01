# Universal Health QR — Chrome / Edge extension (M3)

Manifest V3 side panel for **demo hospital pages only** (`localhost:5173` Hospital A, `localhost:5174` Hospital B). Not a universal EHR scraper.

## Load unpacked (Chrome or Edge)

1. Start demos:
   ```powershell
   cd "D:\My Team Projects\QrCode-Card\apps\hospital-a-demo"; npm run dev
   cd "D:\My Team Projects\QrCode-Card\apps\hospital-b-demo"; npm run dev
   ```
2. Open `chrome://extensions` (or `edge://extensions`) → enable **Developer mode**.
3. **Load unpacked** → select this `extension/` folder.
4. Pin “Universal Health QR” → click icon to open the **side panel**.
5. Sign in with demo credentials (points at `https://codebase.flowlab.fun` by default).
6. On Hospital A: save a final prescription; side panel shows page sync marker when present.
7. On Hospital B: paste opaque QR token (or camera scan if supported) → Resolve → history → **Prefill demographics (confirm)**.

## Safety

- Host permissions limited to demo origins + API.
- Tokens stay in the service worker / `chrome.storage` — not injected into page DOM for auth.
- Prefill runs only after explicit confirmation and only for `data-uhq-field` approved fields on Hospital B.

## Synthetic data only
