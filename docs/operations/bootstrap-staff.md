# Bootstrap First Staff (Admin) User

Register endpoint (`POST /api/v1/auth/register`) only accepts `role: "patient" | "doctor"`. Staff cannot self-register — you must promote an existing user.

Two supported paths: **env-managed** (recommended, auditable) or **direct DB** (one-off bootstrap).

---

## Prerequisite

The target user must already exist — register normally as `patient` or `doctor` first via the web UI or API, then promote them.

---

## Path A — Env-managed promotion (recommended)

Uses `STAFF_ALLOWLIST` + `STAFF_SYNC_MODE`. The sync runs lazily on the next authenticated request, and automatically **demotes** anyone removed from the list, so the env var is the source of truth.

### 1. Confirm migrations are applied

`staff_management_states` table must exist:

```bash
python3 -m migrations.run_all
```

### 2. Dry-run first

Edit `app/.env` (local) or Vercel project env (prod):

```bash
STAFF_ALLOWLIST=user:5            # or email:you@example.com, phone:+66..., telegram:...
STAFF_SYNC_MODE=dry-run
```

Restart the API, trigger any authenticated request (e.g. open the web app), then check logs:

```
[staff-sync] Would promote user 5 (patient -> staff)
```

If the wrong user would be promoted — fix the allowlist before continuing.

### 3. Apply

```bash
STAFF_SYNC_MODE=apply
```

Restart. On the next request the user's `role` flips to `staff` in the DB and a row is written to `staff_management_states` (so the system remembers to demote them if they drop out of the allowlist).

### 4. Verify

Log in as that user → `/dashboard` now shows the Membership Admin panel. The "System: Backups" link in the top-right links to `/admin/system/backups`.

### Allowlist entry formats

| Prefix | Example | Notes |
|--------|---------|-------|
| `user:` | `user:5` | User ID — most reliable |
| `email:` | `email:you@example.com` | Hashed match against `users.email_hash` |
| `phone:` | `phone:+66800000000` | Hashed match against `users.phone_number_hash` |
| `telegram:` | `telegram:123456789` | Telegram user ID |

Multiple entries are comma-separated: `user:5,email:admin@example.com`.

### Special values

- **Unset** — no sync, no access filter. Role comes from DB only. Fine for local dev.
- **`STAFF_ALLOWLIST=NONE`** + `apply` — **demotes all env-managed staff**. Use only when you want to clear out previously promoted users.
- **Empty string** — same as unset (warning logged).

### What `apply` actually does

Per request, for users whose signature changed:

- In allowlist & not staff → **promote** (`role = "staff"`, row added to `staff_management_states`).
- In `staff_management_states` but not in allowlist → **demote** back to `original_role`, metadata row deleted.
- Already staff and in allowlist → unchanged.

Manually promoted staff (Path B below, without a `staff_management_states` row) are **not** touched by sync.

---

## Path B — Direct DB promotion (one-off bootstrap)

Only use this if Path A is blocked (e.g. migrations haven't run and you need access to run them). This bypasses `staff_management_states` so the user will **not** be auto-demoted later.

### SQLite (local)

```bash
sqlite3 blood_pressure.db
> UPDATE users SET role='staff' WHERE id=5;
> .quit
```

### PostgreSQL (Neon / prod)

```bash
psql "$DATABASE_URL"
=> UPDATE users SET role='staff' WHERE id=5;
=> \q
```

Then set `STAFF_ALLOWLIST` with that user so they remain whitelisted even after the feature is fully rolled out:

```bash
STAFF_ALLOWLIST=user:5
STAFF_SYNC_MODE=apply
```

Without the allowlist entry, if `STAFF_ALLOWLIST=NONE` is ever set the manually-promoted user stays as `staff` (no `staff_management_states` row means sync ignores them), but endpoints guarded by `require_staff` will still reject access because `is_staff_access_allowed` returns `False` when the filter is enforced.

---

## Verifying access

```bash
# 1. Login → copy JWT from cookie or response
# 2. Hit an admin endpoint
curl -H "Authorization: Bearer <JWT>" \
     -H "X-API-Key: bp-web-app-key" \
     https://your-api/api/v1/admin/users
```

Expected: `200 OK` with masked user list. If `403 "Staff access denied"` → allowlist doesn't match; `403 "Staff access required"` → DB role isn't `staff`.

---

## Troubleshooting

| Symptom | Likely cause |
|---------|-------------|
| Dashboard shows patient view for a staff user | Browser has stale `user` cookie — log out / log back in |
| `403 Staff access denied` on admin endpoints | `STAFF_ALLOWLIST` set but user not in it |
| `[staff-sync] Metadata table 'staff_management_states' is missing` | Run `python3 -m migrations.run_all` |
| Allowlist change doesn't take effect | Sync only re-runs when `STAFF_ALLOWLIST`+`STAFF_SYNC_MODE` signature changes, or after a cold start; restart the API process |
| Vercel: sync never runs | Each serverless invocation has a fresh process, so sync runs on first authenticated request per instance — that's expected |

---

## See also

- [BACKUP_AND_MIGRATION_SPEC](../../plan/v2-asm-org-support/BACKUP_AND_MIGRATION_SPEC.md) — superadmin-only backup tool that requires this bootstrap step first.
- [CLAUDE.md](../../CLAUDE.md) §Staff Admin Panel — endpoint reference.
- [staff_sync.py](../../app/utils/staff_sync.py) — authoritative implementation.
