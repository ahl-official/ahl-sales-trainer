
import sys
import os
import unittest
from unittest.mock import patch
import json

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from extensions import db

class TestReportFallback(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        
        # Setup DB
        db.initialize()
        
        # Create user with unique name
        import time
        self.username = f'testuser_{int(time.time())}'
        self.user_id = db.create_user(self.username, 'password', 'Test User', 'candidate')
        
        # Create session
        self.session_id = db.create_session(self.user_id, 'Sales Objections', 'beginner', 10)
        
        # Login
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user_id
            
        conn = db._get_connection()
        cur = conn.cursor()
        
        # Insert question into question_bank
        cur.execute("""
            INSERT INTO question_bank 
            (session_id, position, question_text, expected_answer, source, difficulty) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (self.session_id, 1, 'What is the price?', 'It depends.', 'sales_manual', 'beginner'))
        q_id = cur.lastrowid
        
        # Insert evaluation
        cur.execute("""
            INSERT INTO answer_evaluations 
            (session_id, question_id, user_answer, feedback, overall_score) 
            VALUES (?, ?, ?, ?, ?)
        """, (self.session_id, q_id, 'It is expensive', 'Not good', 5.0))
        
        conn.commit()
        conn.close()

    def tearDown(self):
        # Clean up
        db.delete_session(self.session_id)
        self.app_context.pop()

    @patch('routes.training_routes.build_candidate_report_html')
    def test_fallback_report(self, mock_build):
        # Force primary builder to fail
        mock_build.side_effect = Exception("Primary builder failed!")
        
        print(f"Testing report generation for session {self.session_id} with fallback...")
        
        response = self.client.get(f'/api/training/report/{self.session_id}')
        
        print(f"Response status: {response.status_code}")
        data = response.get_json()
        if not data:
             print("No JSON data returned!")
             print(response.data)
             
        # print(f"Response data keys: {data.keys()}")
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data.get('success'))
        self.assertIn('report_html', data)
        report_html = data['report_html']
        
        # Verify fallback content
        self.assertIn('Session Summary', report_html)
        self.assertIn('What is the price?', report_html)
        self.assertIn('It is expensive', report_html)
        self.assertIn('It depends.', report_html)
        
        print("Fallback report content verification passed!")

if __name__ == '__main__':
    unittest.main()
