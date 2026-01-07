from functools import wraps
from flask import session, jsonify
from extensions import db

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'authentication_required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'authentication_required'}), 401
        user = db.get_user_by_id(session['user_id'])
        if not user or user['role'] != 'admin':
            return jsonify({'error': 'admin_required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': 'authentication_required'}), 401
            user = db.get_user_by_id(session['user_id'])
            if not user or user.get('role') not in allowed_roles:
                return jsonify({'error': 'forbidden'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
