"""
One-time migration: drops the old sam_bids / septa_quotes tables and
recreates them (plus the new scrape_jobs table) with the current schema.

Run ONCE from the server directory:
    python migrate.py

Safe to re-run — uses IF EXISTS so it won't error on missing tables.
"""

from database import engine, create_db_and_tables
from sqlalchemy import text

# ── Import all models so SQLModel.metadata knows about every table ────────────
# Without these imports SQLModel.metadata is empty and create_db_and_tables()
# will not create any of the application tables.
import models  # noqa: F401  — side-effect: registers all SQLModel classes

_DROP = """
DROP TABLE IF EXISTS septa_quotes  CASCADE;
DROP TABLE IF EXISTS sam_bids      CASCADE;
DROP TABLE IF EXISTS scrape_jobs   CASCADE;
DROP TABLE IF EXISTS naics_codes   CASCADE;
"""

def main():
    print("Dropping old tables (sam_bids, septa_quotes, scrape_jobs, naics_codes)...")
    with engine.connect() as conn:
        conn.execute(text(_DROP))
        conn.commit()
    print("Tables dropped.")

    print("Re-creating all tables with the current schema...")
    create_db_and_tables()
    print("Done — tables created:")
    print("  scrape_jobs, sam_bids, septa_quotes, naics_codes, unison_requests, dibbs_bids")

if __name__ == "__main__":
    main()
