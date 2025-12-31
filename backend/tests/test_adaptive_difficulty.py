import json


def test_topic_based_followup_selection(client, db):
    user_id = db.create_user("adaptive_user", "pass", "Adaptive User", "candidate")
    client.post('/api/auth/login', json={'username': 'adaptive_user', 'password': 'pass'})

    session_id = db.create_session(user_id, "General Sales", "basic", 10)

    db.save_prepared_questions(session_id, [
        {
            'question': 'Budget question 1',
            'expected_answer': 'Talk about budget',
            'key_points': ['budget'],
            'source': 'Video 1',
            'difficulty': 'basic',
            'is_objection': False
        },
        {
            'question': 'Budget question 2',
            'expected_answer': 'More about budget',
            'key_points': ['budget'],
            'source': 'Video 2',
            'difficulty': 'basic',
            'is_objection': False
        },
        {
            'question': 'Transplant question',
            'expected_answer': 'Transplant explanation',
            'key_points': ['transplant'],
            'source': 'Video 3',
            'difficulty': 'basic',
            'is_objection': False
        }
    ])

    qs = db.get_session_questions(session_id)
    budget_q1 = [q for q in qs if 'Budget question 1' in q['question_text']][0]
    budget_q2 = [q for q in qs if 'Budget question 2' in q['question_text']][0]
    transplant_q = [q for q in qs if 'Transplant question' in q['question_text']][0]

    db.save_answer_evaluation(session_id, budget_q1['id'], {
        'user_answer': 'Bad budget answer',
        'overall_score': 3,
        'feedback': 'Weak budget handling',
        'evidence_from_training': '',
    })

    resp = client.post('/api/training/get-next-question', json={'session_id': session_id})
    assert resp.status_code == 200
    data = resp.get_json()
    q = data['question']
    assert q['id'] in (budget_q2['id'],)

