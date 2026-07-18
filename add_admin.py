import sqlite3
from werkzeug.security import generate_password_hash

# db_path = r"instance/port2.db"

# conn = sqlite3.connect(db_path)
# cur = conn.cursor()

username = "admin2@.com"

# # Hash password
raw_password = "SCM1233@"   # your admin password
password_hash = generate_password_hash(raw_password)

# cur.execute("""
# INSERT INTO admin_users (username, password_hash)
# VALUES (?, ?)
# """, (username, password_hash))

# conn.commit()
# conn.close()

# print("Admin inserted with hashed password!")


from app import db

db.session.execute("ALTER TABLE material ADD COLUMN material_type TEXT")
db.session.commit()
