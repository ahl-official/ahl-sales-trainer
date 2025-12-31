import requests
import time
import sys

BASE_URL = "http://localhost:5050/api"

def test_audit_logging():
    print("Testing audit logging...")
    
    # 1. Login as admin
    print("1. Logging in as admin...")
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "admin",
        "password": "adminpassword"
    })
    
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        return False
        
    admin_id = response.json()['user']['id']
    print("   Login successful")
    
    # 2. Get audit logs
    print("2. Fetching audit logs...")
    # Need to preserve cookies for session
    cookies = response.cookies
    
    response = requests.get(f"{BASE_URL}/admin/audit-logs", params={
        "limit": 5,
        "action": "login_success"
    }, cookies=cookies)
    
    if response.status_code != 200:
        print(f"Failed to fetch audit logs: {response.text}")
        return False
        
    logs = response.json()['logs']
    print(f"   Found {len(logs)} login logs")
    
    # 3. Verify latest log
    if not logs:
        print("   No logs found!")
        return False
        
    latest_log = logs[0]
    print(f"   Latest log: {latest_log['action']} by user {latest_log['user_id']}")
    
    if latest_log['action'] == 'login_success' and latest_log['user_id'] == admin_id:
        print("   ✅ Audit log verification successful")
        return True
    else:
        print("   ❌ Audit log verification failed")
        return False

if __name__ == "__main__":
    if test_audit_logging():
        sys.exit(0)
    else:
        sys.exit(1)
