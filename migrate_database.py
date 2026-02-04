"""
Database migration script to add user_id to tasks table
"""

import sqlite3
import os
from datetime import datetime

def migrate_database():
    """Migrate database to add user_id column and users table if needed"""
    db_path = os.path.join(os.path.dirname(__file__), "tasks.db")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("[MIGRATION] Starting database migration...")
        
        # First, create users table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        print("[OK] Users table created/verified")
        
        # Check if user_id column exists in tasks table
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'user_id' not in columns:
            print("[!] user_id column not found in tasks table - adding it...")
            
            # Check if tasks table exists first
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")
            if cursor.fetchone():
                # Tasks table exists but needs user_id
                # We'll add user_id with a default user_id of 1
                try:
                    cursor.execute("ALTER TABLE tasks ADD COLUMN user_id INTEGER DEFAULT 1")
                    print("[OK] Added user_id column to tasks table (default: 1)")
                except sqlite3.OperationalError as e:
                    if "column user_id already exists" in str(e):
                        print("[OK] user_id column already exists")
                    else:
                        print(f"[!] Error adding column: {e}")
                        raise
            else:
                # Recreate tasks table with user_id
                print("[!] Tasks table needs to be recreated with user_id column...")
        else:
            print("[OK] user_id column already exists in tasks table")
        
        # Ensure default user exists (for backward compatibility with existing tasks)
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        if user_count == 0:
            print("[!] No users found - creating default user...")
            cursor.execute("""
                INSERT INTO users 
                (username, email, password_hash, created_at, updated_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                "default_user",
                "default@example.com",
                "pbkdf2:sha256:600000$default",  # Dummy hash
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                1
            ))
            print("[OK] Default user created (ID: 1)")
        else:
            print(f"[OK] {user_count} users found in database")
        
        conn.commit()
        conn.close()
        
        print("\n[OK] Database migration completed successfully!")
        return True
        
    except sqlite3.Error as e:
        print(f"[ERROR] Database migration failed: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error during migration: {e}")
        return False


if __name__ == "__main__":
    success = migrate_database()
    exit(0 if success else 1)
