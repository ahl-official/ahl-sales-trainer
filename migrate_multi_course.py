import sqlite3
import os

DB_PATH = 'data/sales_trainer.db'

DEFAULT_CATEGORIES = [
    'Pre Consultation',
    'Consultation Series',
    'Sales Objections',
    'After Fixing Objection',
    'Full Wig Consultation',
    'Hairline Consultation',
    'Types of Patches',
    'Upselling / Cross Selling',
    'Retail Sales',
    'SMP Sales',
    'Sales Follow up',
    'General Sales'
]

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    # Enable FK support
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    print("🚀 Starting Multi-Course Migration...")

    try:
        # 1. Create courses table
        print("Creating 'courses' table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 2. Create course_categories table
        print("Creating 'course_categories' table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS course_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                display_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
                UNIQUE(course_id, name)
            )
        ''')

        # 3. Insert Default "Sales Trainer" Course
        print("Ensuring default 'Sales Trainer' course exists...")
        cursor.execute('''
            INSERT INTO courses (id, name, slug, description) 
            VALUES (1, 'Sales Trainer', 'sales', 'Master the art of sales consultations and objection handling.')
            ON CONFLICT(id) DO UPDATE SET name=excluded.name
        ''')

        # 4. Populate Categories for Course 1
        print("Populating default categories...")
        for idx, cat in enumerate(DEFAULT_CATEGORIES):
            cursor.execute('''
                INSERT INTO course_categories (course_id, name, display_order)
                VALUES (1, ?, ?)
                ON CONFLICT(course_id, name) DO NOTHING
            ''', (cat, idx))

        # 5. Add course_id to sessions
        print("Checking 'sessions' table schema...")
        cursor.execute("PRAGMA table_info(sessions)")
        cols = [r[1] for r in cursor.fetchall()]
        if 'course_id' not in cols:
            print("Adding 'course_id' to sessions...")
            # SQLite limitation workaround: Add column without FK constraint first
            cursor.execute("ALTER TABLE sessions ADD COLUMN course_id INTEGER DEFAULT 1")
        else:
            print("✅ 'sessions' already has course_id.")

        # 6. Add course_id to uploads
        print("Checking 'uploads' table schema...")
        cursor.execute("PRAGMA table_info(uploads)")
        cols = [r[1] for r in cursor.fetchall()]
        if 'course_id' not in cols:
            print("Adding 'course_id' to uploads...")
            # SQLite limitation workaround: Add column without FK constraint first
            cursor.execute("ALTER TABLE uploads ADD COLUMN course_id INTEGER DEFAULT 1")
        else:
            print("✅ 'uploads' already has course_id.")

        # 7. Add Indexes
        print("Creating indexes for performance...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_course_id ON sessions(course_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_uploads_course_id ON uploads(course_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_course_categories_course_id ON course_categories(course_id)")

        conn.commit()
        print("✅ Migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
