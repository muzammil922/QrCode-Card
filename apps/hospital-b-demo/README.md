# Hospital B demo (Ridge Clinic B)

Vite + React + TypeScript chart intake for **Demo Hospital B**.

Resolves a patient by UHID, opaque QR token, or patient id, then loads authorized synced FHIR-aligned records (prescriptions from Hospital A) with provenance.

## Run

```powershell
cd "D:\My Team Projects\QrCode-Card\apps\hospital-b-demo"
Copy-Item .env.example .env   # optional; defaults to Flowlab API
npm install
npm run dev
```

Open http://localhost:5174 (port differs from Hospital A’s 5173).

| Env | Default |
|-----|---------|
| `VITE_API_BASE` | `https://codebase.flowlab.fun` |
| `VITE_DEMO_USERNAME` / `VITE_DEMO_PASSWORD` | demo stub credentials |

For a local API: set `VITE_API_BASE=http://localhost:8000`.
