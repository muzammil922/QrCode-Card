# Universal Health QR — Chrome / Edge extension (M3)

Manifest V3 side panel for **demo hospital pages only** (`localhost:5173` Hospital A, `localhost:5174` Hospital B). Not a universal EHR scraper.

## Where do you test? (important)

| Environment | Status |
|-------------|--------|
| **Demo Hospital A/B** (this repo, Vite) | **Yes — use this now** |
| Swagger / API `codebase.flowlab.fun` | Yes (API path) |
| Real hospital software (Epic, etc.) | **Not yet** — needs Phase 3 + written hospital permission + a custom adapter |

Abhi **kisi real hospital EHR pe mat test karo**. Pehle demo pages + extension.

## Input devices supported

| Device | How it works in this extension |
|--------|--------------------------------|
| **Webcam / laptop camera** | Side panel → **Camera scan** (Chrome `BarcodeDetector`) |
| **USB barcode / QR scanner** | Usually “keyboard wedge”: click **Scanner / tap focus** box → scan → auto Enter → resolve |
| **NFC / tap reader** (HID keyboard mode) | Same as scanner: focus the box → tap card that encodes the opaque token |
| **Phone** | Print/show QR from patient card → scan with camera or USB scanner |

Configure your scanner to send **suffix Enter** (most do by default).

## Load unpacked (Chrome or Edge)

1. Start demos (`npm run dev` on A `:5173` and B `:5174`).
2. `chrome://extensions` → Developer mode → **Load unpacked** → this `extension/` folder.
3. After code updates: click **Reload** on the extension card.
4. Open side panel → login → focus scanner box or use camera.

## Safety

- Host permissions: demo origins + API only.
- Prefill on Hospital B only after confirm.
- Opaque QR only — no PHI in the code.
