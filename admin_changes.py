# create_tables.py

#sqllite
import sqlite3

db_path = r"dbpaths"

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Create admin table
cur.execute("""
CREATE TABLE IF NOT EXISTS admin_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
""")

conn.commit()
conn.close()

print("Admin table created successfully at:", db_path)
