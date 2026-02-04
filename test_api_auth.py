"""
Test API Authentication Endpoints
"""

import requests
import json

BASE_URL = 'http://localhost:5000'

def test_signup():
    """Test signup endpoint"""
    print("\n[TEST] User Signup via API")
    print("=" * 70)
    
    data = {
        'username': 'alice',
        'email': 'alice@example.com',
        'password': 'SecurePass123'
    }
    
    response = requests.post(f'{BASE_URL}/api/auth/signup', json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.json().get('user_id')


def test_login(username, password):
    """Test login endpoint"""
    print("\n[TEST] User Login via API")
    print("=" * 70)
    
    data = {
        'username': username,
        'password': password
    }
    
    response = requests.post(f'{BASE_URL}/api/auth/login', json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.json().get('token')


def test_verify_session(token=None):
    """Test session verification"""
    print("\n[TEST] Verify Session")
    print("=" * 70)
    
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    response = requests.get(f'{BASE_URL}/api/auth/verify-session', headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")


def test_profile(token=None):
    """Test get profile endpoint"""
    print("\n[TEST] Get User Profile")
    print("=" * 70)
    
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    response = requests.get(f'{BASE_URL}/api/auth/profile', headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("API AUTHENTICATION TEST".center(70))
    print("=" * 70)
    
    # Test signup
    user_id = test_signup()
    
    # Test login
    token = test_login('alice', 'SecurePass123')
    
    # Test session verification
    test_verify_session(token)
    
    # Test get profile
    test_profile(token)
    
    print("\n" + "=" * 70)
    print("All API tests completed!")
    print("=" * 70 + "\n")
