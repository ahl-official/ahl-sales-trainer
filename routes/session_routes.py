from flask import Blueprint, send_file, session, jsonify
from utils.decorators import login_required
from extensions import db
from config_logging import get_logger

logger = get_logger('session_routes')

session_bp = Blueprint('session', __name__)

@session_bp.route('/<int:session_id>/export/pdf', methods=['GET'])
@login_required
def export_pdf(session_id):
    try:
        session_data = db.get_session(session_id)
        if not session_data:
            return jsonify({'error': 'not_found'}), 404
        
        # Verify ownership or admin based on session data
        if session_data['user_id'] != session.get('user_id') and session.get('role') != 'admin':
            return jsonify({'error': 'unauthorized'}), 403
        
        report_data = db.get_report(session_id) or {'report_html': ''}
        output_path = f"/tmp/session_report_{session_id}.pdf"
        
        from app import generate_session_pdf
        pdf_path = generate_session_pdf(session_data, report_data, output_path)
            
        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'session_report_{session_id}.pdf'
        )
    except Exception as e:
        logger.error(f"PDF export failed: {e}")
        return jsonify({'error': 'server_error'}), 500

@session_bp.route('/user/<int:user_id>', methods=['GET'])
@login_required
def get_user_sessions_route(user_id):
    """Get all sessions for a specific user"""
    # Verify if user is requesting their own sessions or is admin
    if session.get('user_id') != user_id:
        user = db.get_user_by_id(session['user_id'])
        if not user or user['role'] != 'admin':
            return jsonify({'error': 'unauthorized'}), 403
            
    try:
        sessions = db.get_user_sessions(user_id)
        return jsonify({'sessions': sessions})
    except Exception as e:
        logger.error(f"Failed to get user sessions: {e}")
        return jsonify({'error': 'server_error'}), 500
