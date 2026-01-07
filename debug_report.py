
import sys
import os
from database import Database
from report_builder import build_enhanced_report_html, build_candidate_report_html
import logging

# Setup logging to console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_latest_session_report():
    db_path = 'sales_trainer.db'
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    db = Database(db_path)
    
    # Get latest session
    conn = db._get_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM sessions ORDER BY id DESC LIMIT 1')
    row = cur.fetchone()
    conn.close()
    
    if not row:
        print("No sessions found.")
        return

    session = dict(row)
    session_id = session['id']
    user_id = session['user_id']
    print(f"Debugging report for Session ID: {session_id}, User ID: {user_id}")
    
    # Check user
    user = db.get_user_by_id(user_id)
    if not user:
        print(f"User {user_id} not found!")
    else:
        print(f"User found: {user['username']} (Role: {user['role']})")

    # Check questions
    questions = db.get_session_questions(session_id)
    print(f"Found {len(questions)} questions.")
    
    # Check evaluations
    conn = db._get_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM answer_evaluations WHERE session_id = ?', (session_id,))
    evals = cur.fetchall()
    conn.close()
    print(f"Found {len(evals)} evaluations.")
    
    try:
        print("\nAttempting to build enhanced report...")
        report_html = build_enhanced_report_html(db, session_id)
        print("Successfully built enhanced report.")
        print(f"Report length: {len(report_html)} chars")
    except Exception as e:
        print(f"FAILED to build enhanced report: {e}")
        import traceback
        traceback.print_exc()

    try:
        print("\nAttempting to build candidate report...")
        report_html = build_candidate_report_html(db, session_id)
        print("Successfully built candidate report.")
        print(f"Report length: {len(report_html)} chars")
    except Exception as e:
        print(f"FAILED to build candidate report: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_latest_session_report()
