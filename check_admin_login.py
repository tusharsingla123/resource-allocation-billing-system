# from werkzeug.security import check_password_hash
# import sqlite3

# db_path = r"instance/port2.db"

# def verify_admin(username, password):
#     conn = sqlite3.connect(db_path)
#     cur = conn.cursor()

#     cur.execute("SELECT password FROM admin_users WHERE username=?", (username,))
#     row = cur.fetchone()
#     conn.close()

#     if row is None:
#         return False

#     stored_hash = row[0]

#     return check_password_hash(stored_hash, password)

# if verify_admin("admin", "SCM123@"):
#     print("Login successful")
# else:
#     print("Invalid credentials")

## CHECK TABLES

import sqlite3

db_path = r"instance/port2.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cur.fetchall()

print("Tables in database:")
for t in tables:
    print(t[0])

conn.close()
