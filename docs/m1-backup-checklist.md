# M1 pre-deploy backup checklist

Before redeploying M1 migrations to Flowlab production Postgres:

1. In Dokploy → Postgres / Volume Backups: create a backup of database `code`.
2. Confirm you know how to restore that backup.
3. Reply in the project chat: **“DB backup confirmed”**.

M1 migrations are **additive only** (new tables). Existing `organizations` / `users` are not dropped.
