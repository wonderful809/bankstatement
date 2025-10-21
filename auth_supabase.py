"""
Supabase Authentication Module
================================

Handles user authentication using Supabase Auth.
"""

import os
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


class SupabaseAuth:
    """Supabase authentication helper class"""
    
    @staticmethod
    def sign_up(email: str, password: str, name: str = None, plan: str = 'free'):
        """
        Create a new user account with Supabase Auth.
        
        Args:
            email: User's email address
            password: User's password
            name: User's full name (optional)
            plan: Subscription plan (default: 'free')
            
        Returns:
            tuple: (success: bool, message: str, user_data: dict)
        """
        try:
            # Create user with Supabase Auth
            response = supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "name": name,
                        "plan": plan,
                        "pages_used": 0,
                        "created_at": datetime.utcnow().isoformat()
                    }
                }
            })
            
            if response.user:
                return True, "Account created successfully!", {
                    "id": response.user.id,
                    "email": response.user.email,
                    "name": name,
                    "plan": plan,
                    "session": response.session
                }
            else:
                return False, "Failed to create account", None
                
        except Exception as e:
            error_message = str(e)
            if "User already registered" in error_message:
                return False, "Email already registered", None
            elif "Password should be at least 6 characters" in error_message:
                return False, "Password must be at least 6 characters", None
            else:
                return False, f"Error: {error_message}", None
    
    @staticmethod
    def sign_in(email: str, password: str):
        """
        Sign in an existing user.
        
        Args:
            email: User's email address
            password: User's password
            
        Returns:
            tuple: (success: bool, message: str, user_data: dict)
        """
        try:
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user and response.session:
                user_metadata = response.user.user_metadata or {}
                
                return True, "Signed in successfully!", {
                    "id": response.user.id,
                    "email": response.user.email,
                    "name": user_metadata.get("name", ""),
                    "plan": user_metadata.get("plan", "free"),
                    "pages_used": user_metadata.get("pages_used", 0),
                    "session": response.session
                }
            else:
                return False, "Invalid credentials", None
                
        except Exception as e:
            error_message = str(e)
            if "Invalid login credentials" in error_message:
                return False, "Invalid email or password", None
            else:
                return False, f"Error: {error_message}", None
    
    @staticmethod
    def sign_out():
        """
        Sign out the current user.
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            supabase.auth.sign_out()
            return True, "Signed out successfully"
        except Exception as e:
            return False, f"Error signing out: {str(e)}"
    
    @staticmethod
    def get_user(access_token: str):
        """
        Get user data from access token.
        
        Args:
            access_token: JWT access token
            
        Returns:
            dict: User data or None
        """
        try:
            response = supabase.auth.get_user(access_token)
            if response.user:
                user_metadata = response.user.user_metadata or {}
                return {
                    "id": response.user.id,
                    "email": response.user.email,
                    "name": user_metadata.get("name", ""),
                    "plan": user_metadata.get("plan", "free"),
                    "pages_used": user_metadata.get("pages_used", 0)
                }
            return None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    @staticmethod
    def update_user_metadata(access_token: str, metadata: dict):
        """
        Update user metadata (plan, pages_used, etc.).
        
        Args:
            access_token: JWT access token
            metadata: Dictionary of metadata to update
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            response = supabase.auth.update_user({
                "data": metadata
            })
            
            if response.user:
                return True, "User data updated"
            else:
                return False, "Failed to update user data"
                
        except Exception as e:
            return False, f"Error updating user: {str(e)}"
    
    @staticmethod
    def reset_password_email(email: str):
        """
        Send password reset email.
        
        Args:
            email: User's email address
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            supabase.auth.reset_password_for_email(email)
            return True, "Password reset email sent"
        except Exception as e:
            return False, f"Error: {str(e)}"


class User:
    """User class compatible with Flask-Login"""
    
    def __init__(self, user_id, email, name, plan='free', pages_used=0, access_token=None):
        self.id = user_id
        self.email = email
        self.name = name
        self.plan = plan
        self.pages_used = pages_used
        self.access_token = access_token
        
        # Flask-Login requirements
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False
    
    def get_id(self):
        """Required by Flask-Login"""
        return str(self.id)
    
    def can_convert(self, pages: int) -> bool:
        """Check if user can convert given number of pages"""
        plan_limits = {
            'free': 5,
            'starter': 100,
            'professional': 500,
            'business': float('inf')
        }
        
        limit = plan_limits.get(self.plan, 5)
        return self.pages_used + pages <= limit
    
    def update_usage(self, pages: int) -> bool:
        """Update user's page usage"""
        if not self.can_convert(pages):
            return False
        
        self.pages_used += pages
        
        # Update in Supabase
        if self.access_token:
            SupabaseAuth.update_user_metadata(self.access_token, {
                "pages_used": self.pages_used
            })
        
        return True
    
    def get_usage_info(self) -> dict:
        """Get usage statistics"""
        plan_limits = {
            'free': 5,
            'starter': 100,
            'professional': 500,
            'business': float('inf')
        }
        
        limit = plan_limits.get(self.plan, 5)
        remaining = limit - self.pages_used if limit != float('inf') else float('inf')
        
        return {
            'plan': self.plan,
            'pages_used': self.pages_used,
            'pages_limit': limit,
            'pages_remaining': remaining,
            'usage_percentage': (self.pages_used / limit * 100) if limit != float('inf') else 0
        }
    
    def to_dict(self) -> dict:
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'plan': self.plan,
            'pages_used': self.pages_used
        }
    
    @staticmethod
    def from_supabase(user_data: dict) -> 'User':
        """Create User object from Supabase user data"""
        return User(
            user_id=user_data['id'],
            email=user_data['email'],
            name=user_data.get('name', ''),
            plan=user_data.get('plan', 'free'),
            pages_used=user_data.get('pages_used', 0),
            access_token=user_data.get('session', {}).get('access_token') if user_data.get('session') else None
        )


class AnonymousUser:
    """Anonymous user for Flask-Login"""
    
    def __init__(self):
        self.is_authenticated = False
        self.is_active = False
        self.is_anonymous = True
    
    def get_id(self):
        return None
