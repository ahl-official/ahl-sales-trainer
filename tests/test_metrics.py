import json

def test_dashboard_stats_active_today(client, db):
    admin_id = db.create_user("admin", "pass", "Admin", "admin")
    u1 = db.create_user("u1", "p", "User 1", "candidate")
    u2 = db.create_user("u2", "p", "User 2", "candidate")
    
    s1 = db.create_session(u1, "Sales", "Easy", 15)
    s2 = db.create_session(u2, "Sales", "Easy", 15)
    db.complete_session(s1, overall_score=7.5)
    
    client.post('/api/auth/login', json={'username': 'admin', 'password': 'pass'})
    
    resp = client.get('/api/admin/dashboard')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data['stats']['total_candidates'] == 2
    assert data['stats']['completed_sessions'] == 1
    assert 'average_score' in data['stats']
    assert data['stats']['active_today'] >= 2
