import requests
import json
import os
import sqlite3

# Configuration
BASE_URL = 'http://localhost:5000'
DB_PATH = 'sales_trainer.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def setup_test_data():
    """Create a test user and a test course directly in DB"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Create User
    cursor.execute("INSERT OR IGNORE INTO users (username, password_hash, name, role) VALUES (?, ?, ?, ?)", 
                   ('testuser_mc', 'hash', 'Test User MC', 'admin'))
    cursor.execute("SELECT id FROM users WHERE username = ?", ('testuser_mc',))
    user_id = cursor.fetchone()['id']
    
    # 2. Create Course (if not exists)
    cursor.execute("INSERT OR IGNORE INTO courses (slug, name, description) VALUES (?, ?, ?)",
                   ('test-course', 'Test Course', 'A course for testing'))
    cursor.execute("SELECT id FROM courses WHERE slug = ?", ('test-course',))
    course_id = cursor.fetchone()['id']
    
    conn.commit()
    conn.close()
    
    print(f"Test User ID: {user_id}")
    print(f"Test Course ID: {course_id}")
    return user_id, course_id

def test_backend_flow():
    # Setup
    user_id, course_id = setup_test_data()
    
    # Simulate Login (we need to mock session or just trust the DB operations if we test internal logic, 
    # but to test routes we need a valid session. 
    # Since I don't want to implement full login here, I will verify via direct DB checks 
    # or use a test client if I was inside the app context.
    # Given I am outside, I will skip route testing for now and verify the DB logic via a script that imports app)
    pass

if __name__ == "__main__":
    # Instead of requests, I will use the app context to test the service/db layer directly
    # to avoid needing a running server.
    
    from app import app
    from extensions import db
    from services.training_service import prepare_questions
    
    with app.app_context():
        print("Setting up test data...")
        # Create test user
        user_id = db.create_user('test_mc_user', 'password', 'Test MC User', 'admin')
        print(f"Created user {user_id}")
        
        # Create test course
        # We need to manually insert for now as create_course might not be exposed via db object in the same way 
        # or check if db.create_course exists
        try:
            conn = db._get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO courses (slug, name, description) VALUES ('phone-videography', 'Phone Videography', 'Test Course')")
            course_id = cur.lastrowid
            conn.commit()
            conn.close()
            print(f"Created course {course_id}")
        except Exception as e:
            print(f"Course creation failed (maybe exists): {e}")
            # Get the id
            conn = db._get_connection()
            cur = conn.cursor()
            cur.execute("SELECT id FROM courses WHERE slug = 'phone-videography'")
            course_id = cur.fetchone()['id']
            conn.close()
            print(f"Using existing course {course_id}")

        # 1. Test Session Creation with Course ID
        print("\nTesting Session Creation...")
        session_id = db.create_session(
            user_id=user_id,
            category='General Sales',
            difficulty='basics',
            duration_minutes=10,
            mode='standard',
            course_id=course_id
        )
        print(f"Created session {session_id} for course {course_id}")
        
        # Verify in DB
        sess = db.get_session(session_id)
        if sess['course_id'] == course_id:
            print("✅ Session has correct course_id")
        else:
            print(f"❌ Session has wrong course_id: {sess.get('course_id')}")

        # 2. Test Get User Sessions Filtering
        print("\nTesting Get User Sessions Filtering...")
        sessions_course = db.get_user_sessions(user_id, course_id=course_id)
        sessions_default = db.get_user_sessions(user_id, course_id=1)
        
        print(f"Sessions for course {course_id}: {len(sessions_course)}")
        print(f"Sessions for course 1: {len(sessions_default)}")
        
        if len(sessions_course) > 0 and any(s['id'] == session_id for s in sessions_course):
            print("✅ New session found in course specific list")
        else:
            print("❌ New session NOT found in course specific list")
            
        if any(s['id'] == session_id for s in sessions_default):
             print("❌ New session FOUND in default list (Should not happen if course_id != 1)")
        else:
             print("✅ New session NOT found in default list")

        # 3. Test Upload Stats
        print("\nTesting Upload Stats...")
        # Create a dummy upload for this course
        db.create_upload_record('General Sales', 'Test Video', 'test.txt', 5, user_id, course_id=course_id)
        
        stats = db.get_upload_stats_by_category(course_id=course_id)
        if 'General Sales' in stats and stats['General Sales']['video_count'] > 0:
            print("✅ Upload stats reflect course content")
        else:
             print("❌ Upload stats do not show content")
             
        stats_default = db.get_upload_stats_by_category(course_id=1)
        # Assuming course_id != 1, we shouldn't see this upload there (unless we have other data)
        # But we can't easily verify "not there" without knowing initial state, 
        # but we can verify it IS in the correct course.

        # Cleanup
        print("\nCleaning up...")
        # db.delete_user(user_id) # Be careful with delete_user
        pass
