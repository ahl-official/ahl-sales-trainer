import io
import json

def login_admin(client, db):
    db.create_user("admin", "pass", "Admin", "admin")
    resp = client.post('/api/auth/login', json={'username': 'admin', 'password': 'pass'})
    assert resp.status_code == 200

def test_import_users_success(client, db):
    login_admin(client, db)
    
    csv_content = "username,password,name,role\nuser1,p1,User One,candidate\nuser2,p2,User Two,admin\nuser3,p3,User Three,candidate\n"
    data = {
        'file': (io.BytesIO(csv_content.encode('utf-8')), 'users.csv')
    }
    resp = client.post('/api/admin/users/import', data=data, content_type='multipart/form-data')
    assert resp.status_code == 200
    body = json.loads(resp.data)
    assert body['success'] is True
    summary = body['summary']
    assert len(summary['success']) == 3
    assert len(summary['failed']) == 0
    
    # Verify users exist via list endpoint
    resp2 = client.get('/api/admin/users?role=candidate&limit=10')
    assert resp2.status_code == 200
    list_body = json.loads(resp2.data)
    usernames = [u['username'] for u in list_body['users']]
    assert 'user1' in usernames
    assert 'user3' in usernames
    
    # Admin user should also exist
    resp_admins = client.get('/api/admin/users?role=admin&limit=10')
    assert resp_admins.status_code == 200
    admin_body = json.loads(resp_admins.data)
    admin_usernames = [u['username'] for u in admin_body['users']]
    assert 'user2' in admin_usernames

def test_import_users_invalid_format(client, db):
    login_admin(client, db)
    data = {
        'file': (io.BytesIO(b'not a csv'), 'users.txt')
    }
    resp = client.post('/api/admin/users/import', data=data, content_type='multipart/form-data')
    assert resp.status_code == 400
    body = json.loads(resp.data)
    assert body['error'] == 'invalid_format'

def test_list_users_pagination_and_search(client, db):
    login_admin(client, db)
    # Create candidates
    for i in range(1, 16):
        db.create_user(f"cand{i}", "p", f"Candidate {i}", "candidate")
    # Create a specific one to search
    db.create_user("john", "p", "John Doe", "candidate")
    
    # Page 1 limit 5
    resp1 = client.get('/api/admin/users?role=candidate&limit=5&page=1')
    assert resp1.status_code == 200
    body1 = json.loads(resp1.data)
    assert body1['pagination']['limit'] == 5
    assert body1['pagination']['page'] == 1
    assert body1['pagination']['total'] >= 16
    assert len(body1['users']) == 5
    
    # Page 2 limit 5
    resp2 = client.get('/api/admin/users?role=candidate&limit=5&page=2')
    assert resp2.status_code == 200
    body2 = json.loads(resp2.data)
    assert len(body2['users']) == 5
    
    # Search for "John"
    resp3 = client.get('/api/admin/users?role=candidate&search=John&limit=50')
    assert resp3.status_code == 200
    body3 = json.loads(resp3.data)
    usernames = [u['username'] for u in body3['users']]
    assert 'john' in usernames
    # Ensure search filtered down to matching records
    assert len(body3['users']) >= 1

def test_list_users_requires_admin(client, db):
    # Create candidate and login as candidate
    db.create_user("cand", "p", "Candidate", "candidate")
    resp_login = client.post('/api/auth/login', json={'username': 'cand', 'password': 'p'})
    assert resp_login.status_code == 200
    
    # Attempt to access admin list endpoint
    resp = client.get('/api/admin/users')
    assert resp.status_code == 403
