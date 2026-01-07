from extensions import db
from flask import session

def authenticate_user(username, password):
    """
    Verify user credentials
    Returns user dict if valid, None otherwise
    """
    return db.verify_user(username, password)

def register_user(username, password, name, role='candidate'):
    """
    Register a new user
    Returns user_id
    Raises ValueError if username exists
    """
    existing = db.get_user_by_username(username)
    if existing:
        raise ValueError("Username already exists")
    
    return db.create_user(username, password, name, role)

def get_user_by_id(user_id):
    """Get user by ID"""
    return db.get_user_by_id(user_id)

def list_users(role=None, page=1, limit=10, search=None):
    """List users with pagination"""
    return db.list_users(role, page, limit, search)

def delete_user(user_id):
    """Delete a user"""
    return db.delete_user(user_id)
