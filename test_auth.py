"""
Test User Authentication System
Verify user signup, login, and profile management
"""

import os
import sys
from database import Database
from user_manager import UserManager


def test_auth_system():
    """Test authentication system"""
    
    print("\n" + "=" * 70)
    print("USER AUTHENTICATION SYSTEM TEST".center(70))
    print("=" * 70 + "\n")
    
    # Initialize
    print("[OK] Initializing database...")
    db = Database("tasks.db")
    user_manager = UserManager(db)
    
    # Test 1: User Registration
    print("\n[TEST] User Registration")
    print("-" * 70)
    
    success, msg, user_id = user_manager.register_user(
        "testuser",
        "testuser@example.com",
        "password123"
    )
    print(f"Result: {msg}")
    print(f"User ID: {user_id}")
    assert success, "Registration failed"
    test_user_id = user_id
    
    # Test 2: Duplicate Username
    print("\n[TEST] Duplicate Username Prevention")
    print("-" * 70)
    success, msg, _ = user_manager.register_user(
        "testuser",
        "another@example.com",
        "password123"
    )
    print(f"Result: {msg}")
    assert not success, "Should reject duplicate username"
    
    # Test 3: User Login
    print("\n[TEST] User Login")
    print("-" * 70)
    success, msg, user_id = user_manager.login_user("testuser", "password123")
    print(f"Result: {msg}")
    print(f"User ID: {user_id}")
    assert success, "Login failed"
    assert user_id == test_user_id, "Wrong user ID returned"
    
    # Test 4: Wrong Password
    print("\n[TEST] Wrong Password Detection")
    print("-" * 70)
    success, msg, _ = user_manager.login_user("testuser", "wrongpassword")
    print(f"Result: {msg}")
    assert not success, "Should reject wrong password"
    
    # Test 5: Get User Profile
    print("\n[TEST] Get User Profile")
    print("-" * 70)
    user = user_manager.get_user(test_user_id)
    print(f"Username: {user['username']}")
    print(f"Email: {user['email']}")
    print(f"Active: {user['is_active']}")
    assert user is not None, "Failed to get user"
    
    # Test 6: Update User
    print("\n[TEST] Update User Profile")
    print("-" * 70)
    success = user_manager.update_user(test_user_id, email="newemail@example.com")
    print(f"Update successful: {success}")
    user = user_manager.get_user(test_user_id)
    print(f"New email: {user['email']}")
    assert user['email'] == "newemail@example.com", "Email not updated"
    
    # Test 7: Change Password
    print("\n[TEST] Change Password")
    print("-" * 70)
    success, msg = user_manager.change_password(test_user_id, "password123", "newpassword456")
    print(f"Result: {msg}")
    assert success, "Password change failed"
    
    # Test 8: Login with New Password
    print("\n[TEST] Login with New Password")
    print("-" * 70)
    success, msg, _ = user_manager.login_user("testuser", "newpassword456")
    print(f"Result: {msg}")
    assert success, "Login with new password failed"
    
    # Test 9: List All Users
    print("\n[TEST] List All Users")
    print("-" * 70)
    users = user_manager.list_all_users()
    print(f"Total users: {len(users)}")
    for user in users:
        print(f"  - {user['username']} ({user['email']})")
    
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED!".center(70))
    print("=" * 70 + "\n")


if __name__ == '__main__':
    test_auth_system()
