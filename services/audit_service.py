from flask import session, request
from extensions import db
from config_logging import get_logger

logger = get_logger('audit_service')

def log_audit(action: str, resource_type: str = None, 
              resource_id: int = None, details: str = None):
    """Helper to log audit events"""
    try:
        user_id = session.get('user_id')
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')[:200]
        
        db.log_audit(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    except Exception as e:
        logger.error(f"Failed to log audit event: {e}")
