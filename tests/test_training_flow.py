import pytest
import json


def test_full_training_flow(client, db):
    """Test the complete training session flow"""
    # 1. Setup User
    db.create_user("trainee", "password123", "Trainee User", "candidate")
    
    # 2. Login
    response = client.post('/api/auth/login', json={
        'username': 'trainee',
        'password': 'password123'
    })
    assert response.status_code == 200
    
    # 3. Start Session
    response = client.post('/api/training/start', json={
        'category': 'General Sales',
        'difficulty': 'trial',
        'duration_minutes': 30
    })
    assert response.status_code == 200
    data = json.loads(response.data)
    session_id = data['session_id']
    assert session_id is not None
    
    # Verify session is active in DB
    session = db.get_session(session_id)
    assert session['status'] == 'active'
    
    # 4. End Session (skip chat interaction for this test as it requires external API mocks)
    response = client.post('/api/training/end', json={
        'session_id': session_id
    })
    assert response.status_code == 200
    
    # Verify session is completed
    session = db.get_session(session_id)
    assert session['status'] == 'completed'
    assert session['ended_at'] is not None

def test_admin_monitoring_flow(client, db):
    """Test admin monitoring of training sessions"""
    # 1. Setup Data
    admin_id = db.create_user("admin", "admin123", "Admin User", "admin")
    user_id = db.create_user("candidate1", "pass", "Candidate 1", "candidate")
    
    # Create a completed session
    s_id = db.create_session(user_id, "General Sales", "experienced", 30)
    db.complete_session(s_id, overall_score=8.5)
    
    # 2. Login as Admin
    client.post('/api/auth/login', json={
        'username': 'admin',
        'password': 'admin123'
    })
    
    # 3. View Dashboard Stats
    response = client.get('/api/admin/dashboard/stats')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['total_sessions'] == 1
    
    # 4. Search Sessions
    response = client.get('/api/admin/sessions/search?category=General Sales')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data['sessions']) == 1
    assert data['sessions'][0]['id'] == s_id
    
    # 5. Add Notes to Session
    response = client.put(f'/api/admin/sessions/{s_id}/notes', json={
        'notes': 'Good performance on objection handling'
    })
    assert response.status_code == 200
    
    # Verify notes
    session = db.get_session(s_id)
    assert session['notes'] == 'Good performance on objection handling'

def test_unauthorized_access(client, db):
    """Test security restrictions"""
    # Setup users
    db.create_user("candidate", "pass", "Candidate", "candidate")
    db.create_user("admin", "pass", "Admin", "admin")
    
    # 1. Try accessing admin route without login
    response = client.get('/api/admin/users')
    assert response.status_code == 401
    
    # 2. Login as candidate
    client.post('/api/auth/login', json={
        'username': 'candidate',
        'password': 'pass'
    })
    
    # 3. Try accessing admin route as candidate
    response = client.get('/api/admin/users')
    assert response.status_code == 403
