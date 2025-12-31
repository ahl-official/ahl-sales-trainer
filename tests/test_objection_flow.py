def test_complete_objection_training_session(client, db, monkeypatch):
    db.create_user("testuser", "password123", "Test User", "candidate")
    client.post('/api/auth/login', json={'username': 'testuser', 'password': 'password123'})

    # Start session
    resp = client.post('/api/training/start', json={
        'category': 'Sales Objections',
        'difficulty': 'trial',
        'duration_minutes': 5
    })
    assert resp.status_code == 200
    session_id = resp.get_json()['session_id']

    # Get first question
    resp_q = client.post('/api/training/get-next-question', json={'session_id': session_id})
    assert resp_q.status_code == 200
    data_q = resp_q.get_json()
    assert 'question' in data_q
    question = data_q['question']

    import app as appmod

    def fake_post(url, *args, **kwargs):
        class FakeResp:
            def raise_for_status(self): ...

            def json(self):
                # Minimal valid evaluation payload
                return {
                    "choices": [{
                        "message": {
                            "content": """{
                              "accuracy": 8,
                              "completeness": 8,
                              "clarity": 8,
                              "overall_score": 8,
                              "what_correct": "Handled objection well",
                              "what_missed": "",
                              "what_wrong": null,
                              "feedback": "Good response.",
                              "evidence_from_training": "Master script"
                            }"""
                        }
                    }]
                }

        return FakeResp()

    monkeypatch.setattr(appmod.requests, 'post', fake_post)

    # Evaluate good answer
    resp_eval = client.post('/api/training/evaluate-answer', json={
        'session_id': session_id,
        'question_id': question['id'],
        'user_answer': "Good objection handling answer"
    })
    assert resp_eval.status_code == 200

    # End session and get report
    client.post('/api/training/end', json={'session_id': session_id})
    resp_report = client.get(f'/api/training/report/{session_id}')
    assert resp_report.status_code == 200
    report = resp_report.get_json()
    assert 'report_html' in report
    assert 'Session Summary' in report['report_html']
    assert 'Overall Score' not in report['report_html']
