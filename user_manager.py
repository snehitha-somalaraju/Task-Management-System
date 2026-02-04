"""
User Authentication & Management
Handles user registration, login, and session management
"""

import hashlib
import hmac
import secrets
from datetime import datetime
from typing import Optional, Tuple
from database import Database


class UserManager:
    """Manages user authentication and accounts"""
    
    def __init__(self, db: Database):
        """Initialize UserManager with database connection"""
        self.db = db
    
    # ==================== PASSWORD HASHING ====================
    
    @staticmethod
    def hash_password(password: str, salt: str = None) -> Tuple[str, str]:
        """
        Hash password using PBKDF2 with salt
        Returns: (hashed_password, salt)
        """
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Use PBKDF2 with SHA256
        hashed = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # iterations
        )
        return f"{hashed.hex()}${salt}", salt
    
    @staticmethod
    def verify_password(password: str, stored_hash: str) -> bool:
        """
        Verify password against stored hash
        stored_hash format: hash$salt
        """
        try:
            stored_password_hash, salt = stored_hash.split('$')
            new_hash, _ = UserManager.hash_password(password, salt)
            new_password_hash, _ = new_hash.split('$')
            
            # Use constant-time comparison to prevent timing attacks
            return hmac.compare_digest(stored_password_hash, new_password_hash)
        except Exception as e:
            print(f"Password verification error: {e}")
            return False
    
    # ==================== USER REGISTRATION ====================
    
    def register_user(self, username: str, email: str, password: str) -> Tuple[bool, str, Optional[int]]:
        """
        Register a new user
        
        Args:
            username: User's login name
            email: User's email address
            password: Plain text password (will be hashed)
        
        Returns:
            (success: bool, message: str, user_id: Optional[int])
        """
        try:
            # Validation
            if not username or len(username) < 3:
                return False, "Username must be at least 3 characters", None
            
            if not email or '@' not in email:
                return False, "Valid email is required", None
            
            if not password or len(password) < 6:
                return False, "Password must be at least 6 characters", None
            
            # Check if user already exists
            existing = self.db.execute_query(
                "SELECT id FROM users WHERE username = ? OR email = ?",
                (username, email)
            )
            
            if existing:
                return False, "Username or email already exists", None
            
            # Hash password
            password_hash, _ = self.hash_password(password)
            
            # Insert user
            now = datetime.now().isoformat()
            user_id = self.db.execute_update(
                "INSERT INTO users (username, email, password_hash, created_at, updated_at, is_active) "
                "VALUES (?, ?, ?, ?, ?, 1)",
                (username, email, password_hash, now, now)
            )
            
            print(f"[OK] User registered: {username} (ID: {user_id})")
            return True, "User registered successfully", user_id
        
        except Exception as e:
            print(f"Registration error: {e}")
            return False, f"Registration failed: {str(e)}", None
    
    # ==================== USER LOGIN ====================
    
    def login_user(self, username: str, password: str) -> Tuple[bool, str, Optional[int]]:
        """
        Authenticate user login
        
        Args:
            username: Username or email
            password: Plain text password
        
        Returns:
            (success: bool, message: str, user_id: Optional[int])
        """
        try:
            # Find user by username or email
            user = self.db.execute_query(
                "SELECT id, username, password_hash, is_active FROM users WHERE username = ? OR email = ?",
                (username, username)
            )
            
            if not user:
                return False, "Invalid username or password", None
            
            user_data = dict(user[0])
            
            # Check if user is active
            if not user_data['is_active']:
                return False, "Account is inactive", None
            
            # Verify password
            if not self.verify_password(password, user_data['password_hash']):
                return False, "Invalid username or password", None
            
            user_id = user_data['id']
            print(f"[OK] User logged in: {user_data['username']} (ID: {user_id})")
            return True, "Login successful", user_id
        
        except Exception as e:
            print(f"Login error: {e}")
            return False, f"Login failed: {str(e)}", None
    
    # ==================== USER MANAGEMENT ====================
    
    def get_user(self, user_id: int) -> Optional[dict]:
        """Get user by ID"""
        try:
            result = self.db.execute_query(
                "SELECT id, username, email, created_at, is_active FROM users WHERE id = ?",
                (user_id,)
            )
            if result:
                return dict(result[0])
            return None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[dict]:
        """Get user by username"""
        try:
            result = self.db.execute_query(
                "SELECT id, username, email, created_at, is_active FROM users WHERE username = ?",
                (username,)
            )
            if result:
                return dict(result[0])
            return None
        except Exception as e:
            print(f"Error getting user by username: {e}")
            return None
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        """Update user information"""
        try:
            allowed_fields = {'email', 'username'}
            updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
            
            if not updates:
                return False
            
            # Build update query
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [datetime.now().isoformat(), user_id]
            
            self.db.execute_update(
                f"UPDATE users SET {set_clause}, updated_at = ? WHERE id = ?",
                values
            )
            
            print(f"[OK] User {user_id} updated")
            return True
        except Exception as e:
            print(f"Error updating user: {e}")
            return False
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> Tuple[bool, str]:
        """Change user password"""
        try:
            if len(new_password) < 6:
                return False, "New password must be at least 6 characters"
            
            # Get current password hash
            user = self.db.execute_query(
                "SELECT password_hash FROM users WHERE id = ?",
                (user_id,)
            )
            
            if not user:
                return False, "User not found"
            
            stored_hash = dict(user[0])['password_hash']
            
            # Verify old password
            if not self.verify_password(old_password, stored_hash):
                return False, "Current password is incorrect"
            
            # Hash new password
            new_hash, _ = self.hash_password(new_password)
            
            # Update password
            self.db.execute_update(
                "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
                (new_hash, datetime.now().isoformat(), user_id)
            )
            
            print(f"[OK] Password changed for user {user_id}")
            return True, "Password changed successfully"
        
        except Exception as e:
            print(f"Error changing password: {e}")
            return False, f"Password change failed: {str(e)}"
    
    def delete_user(self, user_id: int) -> bool:
        """Delete user account"""
        try:
            self.db.execute_update(
                "DELETE FROM users WHERE id = ?",
                (user_id,)
            )
            print(f"[OK] User {user_id} deleted")
            return True
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False
    
    def list_all_users(self) -> list:
        """Get all users (admin function)"""
        try:
            users = self.db.execute_query(
                "SELECT id, username, email, created_at, is_active FROM users ORDER BY created_at DESC"
            )
            return [dict(u) for u in users]
        except Exception as e:
            print(f"Error listing users: {e}")
            return []
