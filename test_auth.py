import requests
import json

BASE_URL = "http://localhost:8000"

def test_signup():
    print("Testing signup...")
    response = requests.post(
        f"{BASE_URL}/api/auth/signup",
        json={"email": "test@example.com", "password": "test123456"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 201

def test_login():
    print("\nTesting login...")
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "test@example.com", "password": "test123456"}
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {data}")
    return data.get("access_token") if response.status_code == 200 else None

def test_get_user(token):
    print("\nTesting get current user...")
    response = requests.get(
        f"{BASE_URL}/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

if __name__ == "__main__":
    print("=== Authentication API Tests ===\n")
    
    # Test signup
    signup_success = test_signup()
    
    if signup_success:
        # Test login
        token = test_login()
        
        if token:
            # Test get user
            test_get_user(token)
    
    print("\n=== Tests Complete ===")
