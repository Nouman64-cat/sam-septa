"""
Migration: switch eval_config from allowed_state/territory model to
excluded_service (Rule B) and allowed_service (Rule C) model.

- Deletes all 'allowed_state' and 'territory' rows
- Seeds Rule B excluded services
- Seeds Rule C allowed services
- Leaves 'kill_word' rows untouched
"""

from sqlalchemy import text
from db import engine

EXCLUDED_SERVICES = [
    "maintenance, repair and inspection services",
    "management services",
    "management software",
    "audit",
    "construction & demolition services",
    "rental of equipment",
    "waste management services",
    "promotional services",
    "training services",
    "custodial services",
    "lease of equipment",
    "engineering support services",
    "hotel room booking and lodging",
    "yellow ribbon",
    "food items",
    "religious & education coordinator",
    "real estate",
    "aircraft lavatory services",
    "marine vessel upgrade",
    "research & development",
]

ALLOWED_SERVICES = [
    "cable installation",
    "fence installation",
    "furniture installation",
    "ups / generator repair and maintenance",
    "it hardware / software installation and maintenance",
    "hvac installation, repair and maintenance",
    "industrial hardware installation",
    "roofing installation, repair and maintenance",
    "door / window installation",
    "av equipment installation",
    "storage rack and shelving installation",
]

with engine.connect() as conn:
    # Remove old model rows
    deleted_states = conn.execute(
        text("DELETE FROM eval_config WHERE category = 'allowed_state'")
    ).rowcount
    deleted_territories = conn.execute(
        text("DELETE FROM eval_config WHERE category = 'territory'")
    ).rowcount
    print(f"Deleted {deleted_states} allowed_state row(s), {deleted_territories} territory row(s).")

    # Remove any existing service rows (idempotent re-run)
    conn.execute(text("DELETE FROM eval_config WHERE category = 'excluded_service'"))
    conn.execute(text("DELETE FROM eval_config WHERE category = 'allowed_service'"))

    for svc in EXCLUDED_SERVICES:
        conn.execute(
            text("INSERT INTO eval_config (category, value) VALUES (:cat, :val)"),
            {"cat": "excluded_service", "val": svc},
        )

    for svc in ALLOWED_SERVICES:
        conn.execute(
            text("INSERT INTO eval_config (category, value) VALUES (:cat, :val)"),
            {"cat": "allowed_service", "val": svc},
        )

    conn.commit()
    print(f"Seeded {len(EXCLUDED_SERVICES)} excluded services (Rule B).")
    print(f"Seeded {len(ALLOWED_SERVICES)} allowed services (Rule C).")

    rows = conn.execute(
        text("SELECT category, value FROM eval_config ORDER BY category, value")
    ).fetchall()

print("\nCurrent eval_config rows:")
for r in rows:
    print(f"  [{r[0]}] {r[1]}")
print("Done.")
