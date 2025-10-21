"""
User Authentication Models
===========================

Handles user registration, login, password hashing, and authentication.
Works with both in-memory storage (development) and MongoDB (production).
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import re


# In-memory storage for development (replace with MongoDB in production)
users_db = {}  # {email: user_dict}
users_by_id = {}  # {user_id: user_dict}


class User:
    """User model for authentication"""
    
    def __init__(self, user_id, email, password_hash, name, plan='free', created_at=None):
        self.id = user_id
        self.email = email
        self.password_hash = password_hash
        self.name = name
        self.plan = plan
        self.created_at = created_at or datetime.utcnow()
        self.pages_used = 0
        self.last_reset = datetime.utcnow()
        self.is_active = True
        self.is_authenticated = True
        self.is_anonymous = False
    
    def get_id(self):
        """Required by Flask-Login"""
        return str(self.id)
    
    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'plan': self.plan,
            'pages_used': self.pages_used,
            'last_reset': self.last_reset.isoformat() if self.last_reset else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active
        }
    
    @staticmethod
    def validate_email(email):
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_password(password):
        """Validate password strength"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        if not re.search(r'[0-9]', password):
            return False, "Password must contain at least one number"
        return True, "Password is valid"
    
    @staticmethod
    def create(email, password, name, plan='free'):
        """Create new user"""
        
        # Validate email
        if not User.validate_email(email):
            return None, "Invalid email format"
        
        # Validate password
        is_valid, message = User.validate_password(password)
        if not is_valid:
            return None, message
        
        # Check if email already exists
        if email.lower() in users_db:
            return None, "Email already registered"
        
        # Generate user ID
        user_id = f"user_{len(users_by_id) + 1}_{int(datetime.utcnow().timestamp())}"
        
        # Hash password
        password_hash = generate_password_hash(password)
        
        # Create user
        user = User(
            user_id=user_id,
            email=email.lower(),
            password_hash=password_hash,
            name=name,
            plan=plan
        )
        
        # Store user
        users_db[email.lower()] = user
        users_by_id[user_id] = user
        
        return user, "User created successfully"
    
    @staticmethod
    def get_by_email(email):
        """Get user by email"""
        return users_db.get(email.lower())
    
    @staticmethod
    def get_by_id(user_id):
        """Get user by ID"""
        return users_by_id.get(user_id)
    
    @staticmethod
    def authenticate(email, password):
        """Authenticate user with email and password"""
        
        user = User.get_by_email(email)
        
        if not user:
            return None, "Invalid email or password"
        
        if not user.check_password(password):
            return None, "Invalid email or password"
        
        if not user.is_active:
            return None, "Account is disabled"
        
        return user, "Authentication successful"
    
    @staticmethod
    def get_plan_limits(plan):
        """Get page limits for plan"""
        limits = {
            'free': 5,
            'starter': 100,
            'professional': 500,
            'business': float('inf')
        }
        return limits.get(plan, 5)
    
    def can_convert(self, pages):
        """Check if user can convert given number of pages"""
        
        # Check if monthly reset is needed
        if (datetime.utcnow() - self.last_reset).days >= 30:
            self.pages_used = 0
            self.last_reset = datetime.utcnow()
        
        limit = User.get_plan_limits(self.plan)
        return self.pages_used + pages <= limit
    
    def update_usage(self, pages):
        """Update user's page usage"""
        self.pages_used += pages
        return True
    
    def get_usage_info(self):
        """Get usage information"""
        
        # Check if monthly reset is needed
        if (datetime.utcnow() - self.last_reset).days >= 30:
            self.pages_used = 0
            self.last_reset = datetime.utcnow()
        
        limit = User.get_plan_limits(self.plan)
        
        return {
            'pages_used': self.pages_used,
            'pages_limit': limit,
            'pages_remaining': limit - self.pages_used if limit != float('inf') else 'unlimited',
            'plan': self.plan,
            'last_reset': self.last_reset.isoformat(),
            'percentage_used': (self.pages_used / limit * 100) if limit != float('inf') else 0
        }


class AnonymousUser:
    """Anonymous user class for Flask-Login"""
    
    def __init__(self):
        self.is_authenticated = False
        self.is_active = False
        self.is_anonymous = True
    
    def get_id(self):
        return None
