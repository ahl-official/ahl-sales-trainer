from flask import Blueprint, request, jsonify, session
from services.auth_service import authenticate_user, get_user_by_id
from services.audit_service import log_audit
from utils.decorators import login_required
from validators import LoginRequest
from extensions import limiter

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    """Login endpoint for both admin and candidates"""
    try:
        data = request.json
        
        # Validate input
        login_req = LoginRequest(
            username=data.get('username', ''),
            password=data.get('password', '')
        )
        login_req.validate()
        
        user = authenticate_user(login_req.username.strip(), login_req.password)
        
        if not user:
            # Log failed login attempt
            log_audit('login_failed', details=f"username: {login_req.username}")
            return jsonify({
                'error': 'invalid_credentials',
                'message': 'Invalid username or password'
            }), 401
        
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        
        # Log successful login
        log_audit('login_success', details=f"role: {user['role']}")
        
        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'name': user['name'],
                'role': user['role']
            }
        })
        
    except ValueError as e:
        errs = e.args[0] if e.args else None
        if isinstance(errs, list):
            return jsonify({
                'error': 'validation_error',
                'errors': [{'field': getattr(err, 'field', 'unknown'), 'message': getattr(err, 'message', str(err))} for err in errs]
            }), 400
        return jsonify({'error': 'validation_error', 'message': str(e)}), 400

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Logout endpoint"""
    if 'user_id' in session:
        log_audit('logout')
    session.clear()
    return jsonify({'success': True})

@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """Get current logged-in user info"""
    user = get_user_by_id(session['user_id'])
    if not user:
        return jsonify({'error': 'user_not_found'}), 404
    
    return jsonify({
        'id': user['id'],
        'username': user['username'],
        'name': user['name'],
        'role': user['role']
    })
