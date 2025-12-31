import json
from app import app, db


def test_enhanced_report_generation(client):
    # Create a user and session
    admin = db.get_user_by_username('admin') or {'id': db.create_user('admin_test', 'pass', 'Admin', role='admin')}
    user_id = db.create_user('cand_test', 'pass', 'Candidate')
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'candidate'
        session_id = db.create_session(user_id=user_id, category='Sales Objections', difficulty='basic', duration_minutes=5)
        # Insert one objection and one normal question
        db.save_prepared_questions(session_id, [
            {
                'question': 'Why not a transplant?',
                'expected_answer': 'Donor limitations, density tradeoffs',
                'key_points': ['donor', 'density', 'limitations'],
                'source': 'Script',
                'difficulty': 'basic',
                'is_objection': True
            },
            {
                'question': 'What is maintenance frequency?',
                'expected_answer': 'Every 3-4 weeks',
                'key_points': ['3-4 weeks'],
                'source': 'Video 1',
                'difficulty': 'basic',
                'is_objection': False
            }
        ])
        qs = db.get_session_questions(session_id)
        # Save evaluations
        db.save_answer_evaluation(session_id, qs[0]['id'], {
            'user_answer': 'I think transplant has limits',
            'overall_score': 8.5,
            'clarity': 8,
            'objection_score': 8.5,
            'feedback': 'Good handling',
            'evidence_from_training': 'Donor limits noted',
            'prescribed_language_used': True
        })
        db.save_answer_evaluation(session_id, qs[1]['id'], {
            'user_answer': 'Monthly',
            'overall_score': 6.0,
            'clarity': 6,
            'feedback': 'Close but not exact',
            'evidence_from_training': '3-4 weeks'
        })
        # Fetch report
        resp = c.get(f'/api/training/report/{session_id}')
        assert resp.status_code == 200
        data = resp.get_json()
        html = data['report_html']
        assert 'Session Summary' in html
        assert 'Question' in html
        assert 'Your Answer' in html
        assert 'Expected Answer' in html
        assert 'Overall Score' not in html
