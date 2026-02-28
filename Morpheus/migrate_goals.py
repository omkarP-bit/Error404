"""
One-off migration: add new Goal columns and SavingsActivity table to existing SQLite DB.
Run once: python migrate_goals.py
"""
import sqlite3

DB_PATH = "data/finance.db"
conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

# Check and add existing columns
cur.execute("PRAGMA table_info(goals)")
existing = {row[1] for row in cur.fetchall()}
print(f"Existing goal columns: {sorted(existing)}")

goal_migrations = [
    ("goal_type",           "ALTER TABLE goals ADD COLUMN goal_type TEXT"),
    ("priority",            "ALTER TABLE goals ADD COLUMN priority INTEGER DEFAULT 2"),
    ("feasibility_note",    "ALTER TABLE goals ADD COLUMN feasibility_note TEXT"),
    ("health_tag",          "ALTER TABLE goals ADD COLUMN health_tag TEXT"),
    ("monthly_contribution","ALTER TABLE goals ADD COLUMN monthly_contribution REAL DEFAULT 0.0"),
]

for col, sql in goal_migrations:
    if col not in existing:
        print(f"  Adding column: {col}")
        cur.execute(sql)
    else:
        print(f"  Column already exists: {col}")

# Create savings_activity table if it doesn't exist
cur.execute("""
    CREATE TABLE IF NOT EXISTS savings_activity (
        activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        month_key TEXT NOT NULL,
        contributed INTEGER DEFAULT 0,
        missed INTEGER DEFAULT 0,
        total_sip_amount REAL DEFAULT 0.0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
        UNIQUE(user_id, month_key)
    )
""")
print("  SavingsActivity table created or already exists")

# Create index on user_id and month_key for faster lookups
cur.execute("""
    CREATE INDEX IF NOT EXISTS ix_savings_activity_user_id 
    ON savings_activity(user_id)
""")
cur.execute("""
    CREATE INDEX IF NOT EXISTS ix_savings_activity_month_key 
    ON savings_activity(month_key)
""")

conn.commit()
conn.close()
print("Migration complete.")
