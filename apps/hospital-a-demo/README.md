# Hospital A demo (Harborview A)

Vite + React + TypeScript prescription desk for **Demo Hospital A**.

Creates synthetic patients and final prescriptions, then syncs to Universal Health Cloud **only after** a successful local save. Polls sync status (`queued` → `sent` → `confirmed` / `failed`).

## Run

```powershell
cd "D:\My Team Projects\QrCode-Card\apps\hospital-a-demo"
Copy-Item .env.example .env   # optional; defaults to Flowlab API
npm install
npm run dev
```

Open http://localhost:5173

| Env | Default |
|-----|---------|
| `VITE_API_BASE` | `https://codebase.flowlab.fun` |
| `VITE_DEMO_USERNAME` / `VITE_DEMO_PASSWORD` | demo stub credentials |

For a local API: set `VITE_API_BASE=http://localhost:8000`.
