import sqlite3
import os

db_path = "wireguard_manager.db"

def migrate():
    if not os.path.exists(db_path):
        print("Database file not found. It will be created on next startup.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Adding 'allowed_ips' column to 'node' table...")
        cursor.execute("ALTER TABLE node ADD COLUMN allowed_ips TEXT DEFAULT '0.0.0.0/0, ::/0'")
    except sqlite3.OperationalError:
        print("Column 'allowed_ips' already exists.")

    try:
        print("Adding 'mt_api_port' column to 'node' table...")
        cursor.execute("ALTER TABLE node ADD COLUMN mt_api_port INTEGER DEFAULT 8750")
    except sqlite3.OperationalError:
        print("Column 'mt_api_port' already exists.")

    try:
        print("Adding 'assigned_ip' column to 'user' table...")
        cursor.execute("ALTER TABLE user ADD COLUMN assigned_ip TEXT")
        conn.commit()
        print("Migration successful!")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Column 'assigned_ip' already exists.")
        else:
            print(f"Error during migration: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
