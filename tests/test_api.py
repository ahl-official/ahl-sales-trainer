import pytest
import json

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get('/api/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert 'timestamp' in data
    assert 'db' in data and 'ok' in data['db']
    assert 'rate_limiting' in data
    assert 'mail_configured' in data

def test_login(client, db):
    """Test login functionality"""
    db.create_user("apiuser", "password", "API User", "candidate")
    
    # Success
    response = client.post('/api/auth/login', json={
        'username': 'apiuser',
        'password': 'password'
    })
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    
    # Failure
    response = client.post('/api/auth/login', json={
        'username': 'apiuser',
        'password': 'wrongpassword'
    })
    assert response.status_code == 401

def test_protected_route_access(client):
    """Test access to protected routes without login"""
    # Try to start session without login
    response = client.post('/api/training/start', json={
        'category': 'Sales',
        'difficulty': 'Easy'
    })
    assert response.status_code == 401

def test_admin_route_access(client, db):
    """Test access to admin routes"""
    # Create candidate user
    db.create_user("candidate", "pass", "Candidate", "candidate")
    
    # Login as candidate
    client.post('/api/auth/login', json={
        'username': 'candidate',
        'password': 'pass'
    })
    
    # Try to access admin dashboard
    response = client.get('/api/admin/dashboard/stats')
    assert response.status_code == 403
    
    # Logout
    client.post('/api/auth/logout')
    
    # Create admin user
    db.create_user("admin", "pass", "Admin", "admin")
    
    # Login as admin
    client.post('/api/auth/login', json={
        'username': 'admin',
        'password': 'pass'
    })
    
    # Try to access admin dashboard
    response = client.get('/api/admin/dashboard/stats')
    assert response.status_code == 200

def test_search_api(client, db):
    """Test search API endpoint"""
    # Setup data
    db.create_user("admin", "pass", "Admin", "admin")
    u_id = db.create_user("u1", "p", "User 1", "candidate")
    s_id = db.create_session(u_id, "Sales", "Easy", 30)
    db.complete_session(s_id, overall_score=9.5)
    
    # Login as admin
    client.post('/api/auth/login', json={
        'username': 'admin',
        'password': 'pass'
    })
    
    # Search
    response = client.get('/api/admin/sessions/search?min_score=9.0')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data['sessions']) == 1
    assert data['sessions'][0]['id'] == s_id
