"""Unified migration runner for all manual schema migrations.

Use this as the single entrypoint from task runners and deployment workflows.
Every step is idempotent and safe to re-run.
"""

from migrations import add_admin_audit_log, add_payment_fields, add_staff_management_state, add_timezone_column, migrate_schema


MIGRATIONS = [
    ("base schema fixes", migrate_schema.migrate),
    ("users.timezone", add_timezone_column.migrate),
    ("admin_audit_logs", add_admin_audit_log.migrate),
    ("staff_management_states", add_staff_management_state.migrate),
    ("payments current schema", add_payment_fields.migrate),
]


def run_all() -> None:
    for name, runner in MIGRATIONS:
        print(f"==> Running migration: {name}")
        runner()


if __name__ == "__main__":
    run_all()