import sqlite3
import os

DB_PATH = 'data/sales_trainer.db'

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("Attempting to add 'notes' column to 'sessions' table...")
        cursor.execute("ALTER TABLE sessions ADD COLUMN notes TEXT")
        print("✅ Successfully added 'notes' column.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("ℹ️ 'notes' column already exists.")
        else:
            print(f"❌ Error adding column: {e}")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
