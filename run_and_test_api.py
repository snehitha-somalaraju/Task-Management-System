"""
Start Flask server in background and test auth API
"""

import threading
import time
import requests
import json
from flask_api import app

def run_flask():
    """Run Flask app in background thread"""
    app.run(
        debug=False,
        port=5000,
        host='0.0.0.0',
        use_reloader=False,
        threaded=True,
        use_evalex=False
    )

# Start Flask in background
print("[*] Starting Flask server in background...")
server_thread = threading.Thread(target=run_flask, daemon=True)
server_thread.start()

# Wait for server to start
print("[*] Waiting for server to start...")
time.sleep(3)

# Test endpoints
BASE_URL = 'http://localhost:5000'

print("\n" + "=" * 70)
print("TESTING API AUTHENTICATION ENDPOINTS".center(70))
print("=" * 70 + "\n")

# Test 1: Signup
print("[TEST 1] User Signup")
print("-" * 70)
data = {
    'username': 'alice',
    'email': 'alice@example.com',
    'password': 'SecurePass123'
}

try:
    response = requests.post(f'{BASE_URL}/api/auth/signup', json=data, timeout=5)
    print(f"Status Code: {response.status_code}")
    resp_json = response.json()
    print(json.dumps(resp_json, indent=2))
    user_id = resp_json.get('user_id')
    token = resp_json.get('token')
except Exception as e:
    print(f"Error: {e}")
    user_id = None
    token = None

# Test 2: Login
print("\n[TEST 2] User Login")
print("-" * 70)
login_data = {
    'username': 'alice',
    'password': 'SecurePass123'
}

try:
    response = requests.post(f'{BASE_URL}/api/auth/login', json=login_data, timeout=5)
    print(f"Status Code: {response.status_code}")
    resp_json = response.json()
    print(json.dumps(resp_json, indent=2))
    token = resp_json.get('token')
except Exception as e:
    print(f"Error: {e}")

# Test 3: Get Profile
print("\n[TEST 3] Get User Profile")
print("-" * 70)
headers = {}
if token:
    headers['Authorization'] = f'Bearer {token}'

try:
    response = requests.get(f'{BASE_URL}/api/auth/profile', headers=headers, timeout=5)
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")

# Test 4: Verify Session
print("\n[TEST 4] Verify Session")
print("-" * 70)

try:
    response = requests.get(f'{BASE_URL}/api/auth/verify-session', headers=headers, timeout=5)
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")

# Test 5: Login/Signup page
print("\n[TEST 5] Login Page")
print("-" * 70)

try:
    response = requests.get(f'{BASE_URL}/login', timeout=5)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print(f"Page loaded ({len(response.content)} bytes)")
        print("HTML contains login form:", "login" in response.text.lower())
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 70)
print("Testing complete!")
print("=" * 70 + "\n")

# Keep server running
print("Server is running. Press Ctrl+C to stop.")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nServer stopped.")
