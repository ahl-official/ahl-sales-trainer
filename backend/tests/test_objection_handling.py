import pytest
from app import app, db


def test_sales_objections_generate_objection_questions(client, db):
    user_id = db.create_user("obq_user", "pass", "Objection User", "candidate")
    client.post('/api/auth/login', json={'username': 'obq_user', 'password': 'pass'})

    session_id = db.create_session(user_id, "Sales Objections", "basic", 10)
    resp = client.post('/api/training/prepare', json={'session_id': session_id})
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'questions' in data
    questions = data['questions']
    assert len(questions) > 0
    assert any(q.get('is_objection') for q in questions)


def test_objection_evaluation_fields_present(client, db, monkeypatch):
    user_id = db.create_user("obq_eval_user", "pass", "Eval User", "candidate")
    client.post('/api/auth/login', json={'username': 'obq_eval_user', 'password': 'pass'})

    session_id = db.create_session(user_id, "Sales Objections", "basic", 10)
    resp = client.post('/api/training/prepare', json={'session_id': session_id})
    questions = resp.get_json()['questions']
    q = next(q for q in questions if q.get('is_objection'))

    import app as appmod

    def fake_post(url, *args, **kwargs):
        class FakeResp:
            def raise_for_status(self): ...

            def json(self):
                return {
                    "choices": [{
                        "message": {
                            "content": """{
                              "tone": 8,
                              "technique": 9,
                              "key_points_covered": 8,
                              "closing": 7,
                              "objection_score": 8.5,
                              "overall_score": 8.5,
                              "what_correct": "Explained tradeoff clearly",
                              "what_missed": "",
                              "what_wrong": null,
                              "forbidden_mistakes_made": [],
                              "prescribed_language_used": true,
                              "feedback": "Strong objection handling.",
                              "evidence_from_training": "Master script objection 1"
                            }"""
                        }
                    }]
                }

        return FakeResp()

    monkeypatch.setattr(appmod.requests, 'post', fake_post)

    good_answer = "I understand sir, thin looks natural but does not last long."
    resp_eval = client.post('/api/training/evaluate-answer', json={
        'session_id': session_id,
        'question_id': q['id'],
        'user_answer': good_answer
    })
    assert resp_eval.status_code == 200
    ev = resp_eval.get_json()['evaluation']
    assert 'objection_score' in ev
    assert 'forbidden_mistakes_made' in ev
    assert 'prescribed_language_used' in ev
    assert ev['overall_score'] >= 8

