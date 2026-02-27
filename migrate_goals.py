"""
One-off migration: add new Goal columns to existing SQLite DB.
Run once: python migrate_goals.py
"""
import sqlite3

DB_PATH = "data/finance.db"
conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

cur.execute("PRAGMA table_info(goals)")
existing = {row[1] for row in cur.fetchall()}
print(f"Existing columns: {sorted(existing)}")

migrations = [
    ("goal_type",       "ALTER TABLE goals ADD COLUMN goal_type TEXT"),
    ("priority",        "ALTER TABLE goals ADD COLUMN priority INTEGER DEFAULT 2"),
    ("feasibility_note","ALTER TABLE goals ADD COLUMN feasibility_note TEXT"),
    ("health_tag",      "ALTER TABLE goals ADD COLUMN health_tag TEXT"),
]

for col, sql in migrations:
    if col not in existing:
        print(f"  Adding column: {col}")
        cur.execute(sql)
    else:
        print(f"  Column already exists: {col}")

conn.commit()
conn.close()
print("Migration complete.")
