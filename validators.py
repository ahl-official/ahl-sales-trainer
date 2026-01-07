# backend/validators.py
"""
Input validation functions for all API endpoints
"""
from dataclasses import dataclass
from typing import Optional, List
import re

class ValidationError(Exception):
    """Custom exception for validation errors"""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


@dataclass
class CreateUserRequest:
    """Validation for user creation"""
    username: str
    password: str
    name: str
    role: str = 'candidate'
    
    def validate(self):
        """Validate user creation fields"""
        errors = []
        
        # Username validation
        if not self.username or len(self.username.strip()) < 3:
            errors.append(ValidationError('username', 'Must be at least 3 characters'))
        elif len(self.username) > 50:
            errors.append(ValidationError('username', 'Must be less than 50 characters'))
        elif not re.match(r'^[a-zA-Z0-9._-]+$', self.username):
            errors.append(ValidationError('username', 'Can only contain letters, numbers, dots, dashes, underscores'))
        
        # Password validation
        if not self.password or len(self.password) < 6:
            errors.append(ValidationError('password', 'Must be at least 6 characters'))
        elif len(self.password) > 128:
            errors.append(ValidationError('password', 'Must be less than 128 characters'))
        
        # Name validation
        if not self.name or len(self.name.strip()) < 2:
            errors.append(ValidationError('name', 'Must be at least 2 characters'))
        elif len(self.name) > 100:
            errors.append(ValidationError('name', 'Must be less than 100 characters'))
        
        # Role validation
        if self.role not in ['admin', 'candidate']:
            errors.append(ValidationError('role', 'Must be either "admin" or "candidate"'))
        
        if errors:
            raise ValueError(errors)
        
        return True


@dataclass
class LoginRequest:
    """Validation for login"""
    username: str
    password: str
    
    def validate(self):
        """Validate login fields"""
        errors = []
        
        if not self.username or not self.username.strip():
            errors.append(ValidationError('username', 'Username is required'))
        
        if not self.password:
            errors.append(ValidationError('password', 'Password is required'))
        
        if errors:
            raise ValueError(errors)
        
        return True


@dataclass
class UploadRequest:
    """Validation for content upload"""
    category: str
    video_name: str
    filename: str
    
    VALID_CATEGORIES = [
        'Pre Consultation',
        'Consultation Series',
        'Sales Objections',
        'After Fixing Objection',
        'Full Wig Consultation',
        'Hairline Consultation',
        'Types of Patches',
        'Upselling / Cross Selling',
        'Retail Sales',
        'SMP Sales',
        'Sales Follow up',
        'General Sales'
    ]
    
    def validate(self):
        """Validate upload fields"""
        errors = []
        
        # Category validation
        if not self.category or self.category not in self.VALID_CATEGORIES:
            errors.append(ValidationError('category', f'Must be one of: {", ".join(self.VALID_CATEGORIES)}'))
        
        # Video name validation
        if not self.video_name or len(self.video_name.strip()) < 3:
            errors.append(ValidationError('video_name', 'Must be at least 3 characters'))
        elif len(self.video_name) > 200:
            errors.append(ValidationError('video_name', 'Must be less than 200 characters'))
        
        # Filename validation
        if not self.filename or not self.filename.endswith('.txt'):
            errors.append(ValidationError('filename', 'Must be a .txt file'))
        
        if errors:
            raise ValueError(errors)
        
        return True


@dataclass
class StartSessionRequest:
    """Validation for starting training session"""
    category: str
    difficulty: str
    duration_minutes: int
    
    VALID_CATEGORIES = UploadRequest.VALID_CATEGORIES
    VALID_DIFFICULTIES = ['trial', 'basics', 'field-ready', 'adaptive']
    VALID_DURATIONS = [5, 10, 15, 20, 30]
    
    def validate(self):
        """Validate session start fields"""
        errors = []
        
        # Category validation
        if self.category not in self.VALID_CATEGORIES:
            errors.append(ValidationError('category', 'Invalid category'))
        
        # Difficulty validation
        if self.difficulty not in self.VALID_DIFFICULTIES:
            errors.append(ValidationError('difficulty', f'Must be one of: {", ".join(self.VALID_DIFFICULTIES)}'))
        
        # Duration validation
        if self.duration_minutes not in self.VALID_DURATIONS:
            errors.append(ValidationError('duration_minutes', f'Must be one of: {", ".join(map(str, self.VALID_DURATIONS))}'))
        
        if errors:
            raise ValueError(errors)
        
        return True


@dataclass
class ResumeSessionRequest:
    """Validation for resuming training session"""
    session_id: int
    
    def validate(self):
        """Validate session resume fields"""
        try:
            validate_session_id(self.session_id)
        except ValidationError as e:
            raise ValueError([e])
        return True


def sanitize_html(text: str) -> str:
    """Basic HTML sanitization - remove script tags and dangerous attributes"""
    import html
    
    # Escape HTML entities
    text = html.escape(text)
    
    # Remove any script tags (even after escaping, for extra safety)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove event handlers
    text = re.sub(r'\s*on\w+\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)
    
    return text


def validate_session_id(session_id: any) -> int:
    """Validate and convert session_id to integer"""
    try:
        session_id = int(session_id)
        if session_id < 1:
            raise ValueError("Session ID must be positive")
        return session_id
    except (ValueError, TypeError):
        raise ValidationError('session_id', 'Must be a valid positive integer')


def validate_user_id(user_id: any) -> int:
    """Validate and convert user_id to integer"""
    try:
        user_id = int(user_id)
        if user_id < 1:
            raise ValueError("User ID must be positive")
        return user_id
    except (ValueError, TypeError):
        raise ValidationError('user_id', 'Must be a valid positive integer')
