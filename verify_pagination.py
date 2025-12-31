import requests
import json

BASE_URL = "http://localhost:5050/api"

def verify_pagination():
    # Login as admin
    print("Logging in as admin...")
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "admin",
        "password": "adminpassword"
    })
    
    if response.status_code != 200:
        print("❌ Login failed:", response.text)
        return
        
    cookies = response.cookies
    print("✅ Login successful")
    
    # Test Dashboard Pagination
    print("\nTesting Dashboard Pagination (Page 1, Limit 2)...")
    response = requests.get(f"{BASE_URL}/admin/dashboard", 
                           params={"page": 1, "limit": 2},
                           cookies=cookies)
    
    if response.status_code == 200:
        data = response.json()
        if 'pagination' in data and 'stats' in data:
            print("✅ Dashboard pagination structure correct")
            print(f"   Total: {data['pagination']['total']}")
            print(f"   Page: {data['pagination']['page']}")
            print(f"   Pages: {data['pagination']['pages']}")
            print(f"   Stats: {data['stats']}")
            print(f"   Candidates in response: {len(data['candidates'])}")
            
            if len(data['candidates']) <= 2:
                print("✅ Limit verified")
            else:
                print(f"❌ Limit failed: Got {len(data['candidates'])} candidates")
        else:
            print("❌ Missing pagination or stats in response:", data.keys())
    else:
        print("❌ Dashboard request failed:", response.text)

    # Test Users List Pagination
    print("\nTesting Users List Pagination (Page 1, Limit 2)...")
    response = requests.get(f"{BASE_URL}/admin/users", 
                           params={"page": 1, "limit": 2},
                           cookies=cookies)
                           
    if response.status_code == 200:
        data = response.json()
        if 'pagination' in data and 'users' in data:
            print("✅ Users list pagination structure correct")
            print(f"   Total: {data['pagination']['total']}")
            print(f"   Limit verified: {len(data['users']) <= 2}")
        else:
            print("❌ Missing pagination or users in response")
    else:
        print("❌ Users list request failed")

if __name__ == "__main__":
    verify_pagination()
