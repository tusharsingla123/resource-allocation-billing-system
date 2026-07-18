import sqlite3
import pandas as pd  # optional, for pretty viewing

# ✅ Connect to your database
conn = sqlite3.connect("instance/port2.db")
cursor = conn.cursor()

# 🔹 List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
print(cursor.fetchall())

#🔹 Example: View contents of a table (replace 'users' with your table name)
df = pd.read_sql_query("SELECT * FROM user;", conn)
print(df)

# 🔹 Check table schema
cursor.execute("PRAGMA table_info(users);")
print(cursor.fetchall())

print("Data fetched successfully.")

conn.close()