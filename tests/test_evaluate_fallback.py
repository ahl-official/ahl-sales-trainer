import json


def test_evaluate_answer_fallback(client, db, monkeypatch):
    db.create_user('cand_x', 'pass', 'Candidate X', 'candidate')
    client.post('/api/auth/login', json={'username': 'cand_x', 'password': 'pass'})

    session_id = db.create_session(user_id=db.get_user_by_username('cand_x')['id'], category='Sales Objections', difficulty='basic', duration_minutes=5)
    db.save_prepared_questions(session_id, [{
        'question': 'I want the system to last longer',
        'expected_answer': 'thin vs thick tradeoff',
        'key_points': ['thin', 'thick', 'tradeoff'],
        'source': 'Master Script',
        'difficulty': 'basic',
        'is_objection': True
    }])
    q = db.get_session_questions(session_id)[0]

    # Mock both OpenAI embeddings and OpenRouter chat
    import app as appmod

    def fake_post(url, *args, **kwargs):
        # Simulate failure for both embeddings and chat completion
        raise RuntimeError('network unavailable in test')

    monkeypatch.setattr(appmod.requests, 'post', fake_post)

    resp = client.post('/api/training/evaluate-answer', json={
        'session_id': session_id,
        'question_id': q['id'],
        'user_answer': 'I would prefer longer life'
    })
    assert resp.status_code == 200
    data = resp.get_json()
    ev = data['evaluation']
    assert 'overall_score' in ev
    # Confirm row saved
    conn = db._get_connection()
    cur = conn.cursor()
    cur.execute('SELECT count(*) FROM answer_evaluations WHERE session_id = ?', (session_id,))
    cnt = cur.fetchone()[0]
    conn.close()
    assert cnt == 1
