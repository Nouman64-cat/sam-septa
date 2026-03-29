"""
Migration: replace restricted territories with allowed states.
- Deletes old 'territory' rows
- Seeds all 50 US states as 'allowed_state' rows
"""
from sqlalchemy import text
from db import engine

ALLOWED_STATES = [
    "alabama", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky",
    "louisiana", "maine", "maryland", "massachusetts", "michigan",
    "minnesota", "mississippi", "missouri", "montana", "nebraska",
    "nevada", "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
    "pennsylvania", "rhode island", "south carolina", "south dakota",
    "tennessee", "texas", "utah", "vermont", "virginia",
    "washington", "west virginia", "wisconsin", "wyoming",
]

with engine.connect() as conn:
    # Remove old territory rows
    deleted = conn.execute(
        text("DELETE FROM eval_config WHERE category = 'territory'")
    ).rowcount
    print(f"Deleted {deleted} old territory row(s).")

    # Remove any existing allowed_state rows (idempotent re-run)
    conn.execute(text("DELETE FROM eval_config WHERE category = 'allowed_state'"))

    # Insert 50 allowed states
    for state in ALLOWED_STATES:
        conn.execute(
            text("INSERT INTO eval_config (category, value) VALUES (:cat, :val)"),
            {"cat": "allowed_state", "val": state},
        )

    conn.commit()
    print(f"Seeded {len(ALLOWED_STATES)} allowed states.")

    rows = conn.execute(
        text("SELECT category, value FROM eval_config ORDER BY category, value")
    ).fetchall()

print("\nCurrent eval_config rows:")
for r in rows:
    print(f"  [{r[0]}] {r[1]}")
print("Done.")
