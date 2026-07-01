import sqlite3
import os

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'shop.db')

conn = sqlite3.connect(db_path)
c = conn.cursor()

# Update user table
user_columns = [
    ("is_banned", "BOOLEAN DEFAULT 0"),
    ("banned_reason", "VARCHAR(255)"),
    ("notes", "TEXT"),
    ("last_login", "DATETIME"),
    ("social_provider", "VARCHAR(50)"),
    ("full_name", "VARCHAR(200)"),
    ("avatar", "VARCHAR(200)"),
    ("date_of_birth", "DATE"),
    ("gender", "VARCHAR(20)"),
    ("alt_phone", "VARCHAR(20)"),
    ("profile_complete", "BOOLEAN DEFAULT 0")
]

print("Updating user table...")
for col, ctype in user_columns:
    try:
        c.execute(f"ALTER TABLE user ADD COLUMN {col} {ctype}")
        print(f"Added {col}")
    except sqlite3.OperationalError as e:
        print(f"Skipped {col} - {e}")

# Update admin_user table
admin_columns = [
    ("is_locked", "BOOLEAN DEFAULT 0"),
    ("failed_attempts", "INTEGER DEFAULT 0"),
    ("locked_until", "DATETIME"),
    ("last_login", "DATETIME")
]

print("Updating admin_user table...")
for col, ctype in admin_columns:
    try:
        c.execute(f"ALTER TABLE admin_user ADD COLUMN {col} {ctype}")
        print(f"Added {col}")
    except sqlite3.OperationalError as e:
        print(f"Skipped {col} - {e}")

# Update order table
order_columns = [
    ("address_id", "INTEGER"),
    ("courier_name", "VARCHAR(100)"),
    ("courier_tracking", "VARCHAR(150)"),
    ("order_notes", "TEXT")
]

print("Updating order table...")
for col, ctype in order_columns:
    try:
        c.execute(f"ALTER TABLE \"order\" ADD COLUMN {col} {ctype}")
        print(f"Added {col}")
    except sqlite3.OperationalError as e:
        print(f"Skipped {col} - {e}")

conn.commit()
conn.close()
print("Database schema migration complete.")
