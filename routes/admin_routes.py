from flask import Blueprint, request, jsonify, current_app, session, Response
from services.auth_service import register_user, list_users, delete_user
from services.pinecone_service import process_and_upload
from sync_pinecone_full import sync_pinecone_full
from utils.decorators import admin_required, role_required
from utils.cache import cache_get, cache_set
from extensions import db, limiter
from services.audit_service import log_audit
from import_users import import_users_from_csv
import tempfile
import os
import logging
import io
import csv
import json
from datetime import datetime

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)
viewer_bp = Blueprint('viewer', __name__)

@admin_bp.route('/upload', methods=['POST'])
@admin_required
def upload_content_route():
    if 'file' not in request.files:
        return jsonify({'error': 'no_file'}), 400
        
    file = request.files['file']
    category = request.form.get('category')
    video_name = request.form.get('video_name')
    course_id = request.form.get('course_id', 1, type=int)
    
    if not file or not category or not video_name:
        return jsonify({'error': 'missing_fields'}), 400
        
    if not file.filename.endswith('.txt'):
        return jsonify({'error': 'invalid_format', 'message': 'Only .txt files are supported'}), 400
        
    try:
        # Read content
        content = file.read().decode('utf-8')
        
        # Process and upload to Pinecone
        result = process_and_upload(content, category, video_name, course_id=course_id)
        
        # Save to database
        db.create_upload_record(
            category=category,
            video_name=video_name,
            filename=file.filename,
            chunks_created=result['chunks'],
            uploaded_by=session['user_id'],
            course_id=course_id
        )
        
        return jsonify({
            'success': True,
            'category': category,
            'video_name': video_name,
            'chunks': result['chunks'],
            'course_id': course_id
        })
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return jsonify({'error': 'upload_failed', 'message': str(e)}), 500

@admin_bp.route('/settings', methods=['GET'])
@admin_required
def get_settings():
    """Get all system settings"""
    settings = db.get_all_system_settings()
    return jsonify({'settings': settings})

@admin_bp.route('/settings', methods=['POST'])
@admin_required
def update_settings():
    """Update system settings"""
    data = request.json or {}
    settings = data.get('settings', [])
    
    if not isinstance(settings, list):
        return jsonify({'error': 'invalid_format', 'message': 'Settings must be a list'}), 400
        
    updated = 0
    for s in settings:
        key = s.get('key')
        value = s.get('value')
        
        if key is not None:
            # Use the set_system_setting method which handles upserts
            # We don't update description/type from here usually
            db.set_system_setting(key, value)
            updated += 1
            
    return jsonify({'success': True, 'updated': updated})

@admin_bp.route('/users', methods=['GET'])
@admin_required
def list_users_route():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    role = request.args.get('role')
    search = request.args.get('search')
    
    users, total_count = list_users(role, page, limit, search)
    
    return jsonify({
        'users': users,
        'pagination': {
            'total': total_count,
            'page': page,
            'limit': limit,
            'pages': (total_count + limit - 1) // limit
        }
    })

@admin_bp.route('/users', methods=['POST'])
@admin_required
@limiter.limit("10 per hour")
def create_user_route():
    data = request.json
    try:
        user_id = register_user(
            username=data.get('username', ''),
            password=data.get('password', ''),
            name=data.get('name', ''),
            role=data.get('role', 'candidate')
        )
        return jsonify({'success': True, 'user_id': user_id})
    except ValueError as e:
        return jsonify({'error': 'validation_error', 'message': str(e)}), 400

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user_route(user_id):
    try:
        delete_user(user_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': 'deletion_failed', 'message': str(e)}), 500

@admin_bp.route('/users/import', methods=['POST'])
@admin_required
def import_users_route():
    if 'file' not in request.files:
        return jsonify({'error': 'no_file'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'no_filename'}), 400
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'invalid_format', 'message': 'File must be a CSV'}), 400
        
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp:
            file.save(temp.name)
            temp_path = temp.name
            
        results = import_users_from_csv(temp_path, db_path=db.db_path)
        os.unlink(temp_path)
        
        return jsonify({'success': True, 'summary': results})
    except Exception as e:
        return jsonify({'error': 'import_failed', 'message': str(e)}), 500

@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
def dashboard_route():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    search = request.args.get('search')
    role_filter = request.args.get('role', 'candidate') # Default to candidate if not specified
    course_id = request.args.get('course_id', 1, type=int)
    
    # Get users by role (default 'candidate')
    raw_users, total_count = list_users(role=role_filter, page=page, limit=limit, search=search)
    
    # Enrich users with session stats for dashboard cards
    users_with_stats = []
    for u in raw_users:
        try:
            sessions = db.get_user_sessions(u['id'], course_id=course_id)
            total_sessions = len(sessions)
            completed = [s for s in sessions if (s.get('status') == 'completed')]
            completed_count = len(completed)
            completed_scores = [s.get('overall_score') for s in completed if s.get('overall_score') is not None]
            overall_avg = round(sum(completed_scores) / len(completed_scores), 1) if completed_scores else None
            
            # Category performance breakdown
            cat_perf = {}
            # Sort sessions by started_at descending for latest
            sorted_sessions = sorted(completed, key=lambda s: s.get('started_at') or '', reverse=True)
            for s in sorted_sessions:
                cat = s.get('category') or 'Uncategorized'
                score = s.get('overall_score')
                if cat not in cat_perf:
                    cat_perf[cat] = {'count': 0, 'scores': [], 'latest': None}
                cat_perf[cat]['count'] += 1
                if score is not None:
                    cat_perf[cat]['scores'].append(score)
                # Set latest only once (first in sorted list)
                if cat_perf[cat]['latest'] is None and score is not None:
                    cat_perf[cat]['latest'] = round(score, 1)
            # Convert to average
            for cat, perf in cat_perf.items():
                avg = round(sum(perf['scores']) / len(perf['scores']), 1) if perf['scores'] else 0.0
                cat_perf[cat] = {
                    'count': perf['count'],
                    'average': avg,
                    'latest': perf['latest']
                }
            
            # Difficulty performance breakdown
            diff_perf = {}
            for s in completed:
                diff = (s.get('difficulty') or 'unknown').lower()
                score = s.get('overall_score')
                if diff not in diff_perf:
                    diff_perf[diff] = {'count': 0, 'scores': []}
                diff_perf[diff]['count'] += 1
                if score is not None:
                    diff_perf[diff]['scores'].append(score)
            for dkey, perf in diff_perf.items():
                avg = round(sum(perf['scores']) / len(perf['scores']), 1) if perf['scores'] else 0.0
                diff_perf[dkey] = {
                    'count': perf['count'],
                    'average': avg
                }
            
            users_with_stats.append({
                'user_id': u['id'],
                'username': u.get('username'),
                'name': u.get('name'),
                'role': u.get('role'),
                'total_sessions': total_sessions,
                'completed_sessions': completed_count,
                'overall_average': overall_avg,
                'category_performance': cat_perf,
                'difficulty_performance': diff_perf
            })
        except Exception as e:
            # Fallback to minimal user info if stats fail
            users_with_stats.append({
                'user_id': u['id'],
                'username': u.get('username'),
                'name': u.get('name'),
                'role': u.get('role'),
                'total_sessions': 0,
                'completed_sessions': 0,
                'overall_average': None,
                'category_performance': {},
                'difficulty_performance': {}
            })
    
    # Get stats filtered by the same role
    stats = db.get_global_stats(role=role_filter, course_id=course_id)
    
    return jsonify({
        'candidates': users_with_stats,
        'pagination': {
            'total': total_count,
            'page': page,
            'limit': limit,
            'pages': (total_count + limit - 1) // limit if limit > 0 else 0
        },
        'stats': stats
    })

@admin_bp.route('/sync-content', methods=['POST'])
@admin_required
def sync_content_route():
    try:
        result = sync_pinecone_full()
        if result and 'error' in result:
             return jsonify({'error': 'sync_failed', 'message': result['error']}), 500
        return jsonify(result or {'added': 0, 'deleted': 0})
    except Exception as e:
        return jsonify({'error': 'sync_failed', 'message': str(e)}), 500

@admin_bp.route('/courses', methods=['GET'])
@admin_required
def list_courses_route():
    courses = db.list_courses()
    return jsonify({'courses': courses})

@admin_bp.route('/courses', methods=['POST'])
@admin_required
def create_course_route():
    data = request.json or {}
    name = data.get('name')
    slug = data.get('slug')
    description = data.get('description') or ""
    if not name or not slug:
        return jsonify({'error': 'missing_fields'}), 400
    try:
        cid = db.create_course(name, slug, description)
        return jsonify({'success': True, 'course_id': cid})
    except Exception as e:
        return jsonify({'error': 'create_failed', 'message': str(e)}), 500
        
@admin_bp.route('/courses/<int:course_id>', methods=['DELETE'])
@admin_required
def delete_course_route(course_id):
    try:
        course = db.get_course_by_id(course_id)
        if not course:
            return jsonify({'error': 'not_found'}), 404
        db.delete_course(course_id)
        try:
            details = f"Deleted course '{course.get('name')}' ({course.get('slug')})"
            log_audit('course_deleted', 'course', course_id, details)
        except Exception:
            pass
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': 'delete_failed', 'message': str(e)}), 500

@admin_bp.route('/courses/<int:course_id>/categories', methods=['GET'])
@admin_required
def list_course_categories_route(course_id):
    cats = db.get_course_categories(course_id)
    return jsonify({'categories': cats})

@admin_bp.route('/courses/<int:course_id>/categories', methods=['POST'])
@admin_required
def add_course_category_route(course_id):
    data = request.json or {}
    name = data.get('name')
    display_order = int(data.get('display_order', 0))
    if not name:
        return jsonify({'error': 'missing_name'}), 400
    try:
        cat_id = db.add_course_category(course_id, name, display_order)
        return jsonify({'success': True, 'category_id': cat_id})
    except Exception as e:
        return jsonify({'error': 'create_failed', 'message': str(e)}), 500

@viewer_bp.route('/courses', methods=['GET'])
@role_required(['viewer', 'admin'])
def viewer_list_courses_route():
    try:
        courses = db.list_courses()
        return jsonify({'courses': courses})
    except Exception as e:
        return jsonify({'error': 'server_error'}), 500

@viewer_bp.route('/courses/<int:course_id>/categories', methods=['GET'])
@role_required(['viewer', 'admin'])
def viewer_list_course_categories_route(course_id):
    try:
        cats = db.get_course_categories(course_id)
        return jsonify({'categories': cats})
    except Exception as e:
        return jsonify({'error': 'server_error'}), 500

@admin_bp.route('/dashboard/stats', methods=['GET'])
@admin_required
def get_dashboard_stats():
    # Always compute fresh stats to avoid stale cache during active monitoring/tests
    role = request.args.get('role')
    course_id = request.args.get('course_id', 1, type=int)
    # We only use get_global_stats now as it's more comprehensive and supports role filtering
    global_stats = db.get_global_stats(role=role, course_id=course_id)
    
    # Backwards compatibility keys if frontend expects them from get_dashboard_stats()
    stats = {
        'total_candidates': global_stats['total_candidates'],
        'total_sessions': global_stats['completed_sessions'], # Map completed to total for dashboard card? Or just use completed.
        'avg_score': global_stats['average_score'],
        **global_stats
    }
    return jsonify(stats)

# Viewer read-only endpoints
@viewer_bp.route('/dashboard/stats', methods=['GET'])
@role_required(['viewer', 'admin'])
def viewer_get_dashboard_stats():
    role = request.args.get('role', 'candidate')
    course_id = request.args.get('course_id', 1, type=int)
    global_stats = db.get_global_stats(role=role, course_id=course_id)
    stats = {
        'total_candidates': global_stats['total_candidates'],
        'total_sessions': global_stats['completed_sessions'],
        'avg_score': global_stats['average_score'],
        **global_stats
    }
    return jsonify(stats)

@viewer_bp.route('/dashboard', methods=['GET'])
@role_required(['viewer', 'admin'])
def viewer_dashboard_route():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    search = request.args.get('search')
    role_filter = request.args.get('role', 'candidate')
    course_id = request.args.get('course_id', 1, type=int)
    raw_users, total_count = list_users(role=role_filter, page=page, limit=limit, search=search)
    users_with_stats = []
    for u in raw_users:
        try:
            sessions = db.get_user_sessions(u['id'], course_id=course_id)
            total_sessions = len(sessions)
            completed = [s for s in sessions if (s.get('status') == 'completed')]
            completed_count = len(completed)
            completed_scores = [s.get('overall_score') for s in completed if s.get('overall_score') is not None]
            overall_avg = round(sum(completed_scores) / len(completed_scores), 1) if completed_scores else None
            cat_perf = {}
            sorted_sessions = sorted(completed, key=lambda s: s.get('started_at') or '', reverse=True)
            for s in sorted_sessions:
                cat = s.get('category') or 'Uncategorized'
                score = s.get('overall_score')
                if cat not in cat_perf:
                    cat_perf[cat] = {'count': 0, 'scores': [], 'latest': None}
                cat_perf[cat]['count'] += 1
                if score is not None:
                    cat_perf[cat]['scores'].append(score)
                if cat_perf[cat]['latest'] is None and score is not None:
                    cat_perf[cat]['latest'] = round(score, 1)
            for cat, perf in cat_perf.items():
                avg = round(sum(perf['scores']) / len(perf['scores']), 1) if perf['scores'] else 0.0
                cat_perf[cat] = {
                    'count': perf['count'],
                    'average': avg,
                    'latest': perf['latest']
                }
            diff_perf = {}
            for s in completed:
                diff = (s.get('difficulty') or 'unknown').lower()
                score = s.get('overall_score')
                if diff not in diff_perf:
                    diff_perf[diff] = {'count': 0, 'scores': []}
                diff_perf[diff]['count'] += 1
                if score is not None:
                    diff_perf[diff]['scores'].append(score)
            for dkey, perf in diff_perf.items():
                avg = round(sum(perf['scores']) / len(perf['scores']), 1) if perf['scores'] else 0.0
                diff_perf[dkey] = {
                    'count': perf['count'],
                    'average': avg
                }
            users_with_stats.append({
                'user_id': u['id'],
                'username': u.get('username'),
                'name': u.get('name'),
                'role': u.get('role'),
                'total_sessions': total_sessions,
                'completed_sessions': completed_count,
                'overall_average': overall_avg,
                'category_performance': cat_perf,
                'difficulty_performance': diff_perf
            })
        except Exception:
            users_with_stats.append({
                'user_id': u['id'],
                'username': u.get('username'),
                'name': u.get('name'),
                'role': u.get('role'),
                'total_sessions': 0,
                'completed_sessions': 0,
                'overall_average': None,
                'category_performance': {},
                'difficulty_performance': {}
            })
    stats = db.get_global_stats(role=role_filter, course_id=course_id)
    return jsonify({
        'candidates': users_with_stats,
        'pagination': {
            'total': total_count,
            'page': page,
            'limit': limit,
            'pages': (total_count + limit - 1) // limit if limit > 0 else 0
        },
        'stats': stats
    })
@admin_bp.route('/sessions/bulk-delete', methods=['POST'])
@admin_required
def bulk_delete_sessions():
    data = request.json or {}
    session_ids = data.get('session_ids') or []
    if not isinstance(session_ids, list) or not session_ids:
        return jsonify({'error': 'invalid_input', 'message': 'Provide session_ids as a non-empty list'}), 400
    count = 0
    for sid in session_ids:
        try:
            db.delete_session(int(sid))
            count += 1
        except Exception as e:
            current_app.logger.error(f"Failed to delete session {sid}: {e}")
            # continue deleting others
            continue
    return jsonify({'success': True, 'count': count})

@admin_bp.route('/sessions/<int:session_id>/tags', methods=['PUT'])
@admin_required
def update_session_tags(session_id):
    data = request.json or {}
    tags = data.get('tags')
    if tags is None:
        return jsonify({'error': 'missing_tags'}), 400
    # Normalize input: accept list or comma-separated string
    if isinstance(tags, list):
        tags_str = ",".join([str(t).strip() for t in tags if str(t).strip()])
    else:
        tags_str = ",".join([t.strip() for t in str(tags).split(",") if t.strip()])
    try:
        db.update_session_tags(session_id, tags_str)
        return jsonify({'success': True, 'tags': tags_str})
    except Exception as e:
        logger.error(f"Failed updating tags for session {session_id}: {e}")
        return jsonify({'error': 'update_failed'}), 500

@admin_bp.route('/export/sessions', methods=['GET'])
@admin_required
def export_sessions_csv():
    page = 1
    limit = 1000
    all_rows = []
    # Collect filters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    min_score = request.args.get('min_score', type=float)
    max_score = request.args.get('max_score', type=float)
    category = request.args.get('category')
    role = request.args.get('role')
    search = request.args.get('search')
    course_id = request.args.get('course_id', 1, type=int)
    while True:
        rows, total = db.search_sessions(
            start_date=start_date,
            end_date=end_date,
            min_score=min_score,
            max_score=max_score,
            category=category,
            role=role,
            search_term=search,
            course_id=course_id,
            page=page,
            limit=limit
        )
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < limit:
            break
        page += 1
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'id', 'username', 'candidate_name', 'category', 'started_at', 'ended_at',
        'status', 'duration_minutes', 'difficulty', 'overall_score', 'notes'
    ])
    for r in all_rows:
        writer.writerow([
            r.get('id'),
            r.get('username'),
            r.get('candidate_name'),
            r.get('category'),
            r.get('started_at'),
            r.get('ended_at'),
            r.get('status'),
            r.get('duration_minutes'),
            r.get('difficulty'),
            r.get('overall_score'),
            (r.get('notes') or '')[:500]
        ])
    resp = Response(output.getvalue(), mimetype='text/csv')
    resp.headers['Content-Disposition'] = 'attachment; filename="sessions_export.csv"'
    return resp

@admin_bp.route('/export/users', methods=['GET'])
@admin_required
def export_users_csv():
    page = 1
    limit = 1000
    role = request.args.get('role')
    search = request.args.get('search')
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['id', 'username', 'name', 'role', 'created_at', 'last_login'])
    while True:
        users, total = list_users(role=role, page=page, limit=limit, search=search)
        if not users:
            break
        for u in users:
            writer.writerow([
                u.get('id'),
                u.get('username'),
                u.get('name'),
                u.get('role'),
                u.get('created_at'),
                u.get('last_login')
            ])
        if len(users) < limit:
            break
        page += 1
    resp = Response(output.getvalue(), mimetype='text/csv')
    resp.headers['Content-Disposition'] = 'attachment; filename=\"users_export.csv\"'
    return resp

@admin_bp.route('/saved-views', methods=['GET'])
@admin_required
def list_saved_views():
    admin_id = session.get('user_id')
    views = db.list_views(admin_id)
    return jsonify({'views': views})

@admin_bp.route('/saved-views', methods=['POST'])
@admin_required
def save_view():
    admin_id = session.get('user_id')
    payload = request.json or {}
    name = payload.get('name')
    filters = payload.get('filters') or {}
    shared = payload.get('shared', False)
    
    if not name:
        return jsonify({'error': 'missing_name'}), 400
    try:
        vid = db.save_view(admin_id, name, json.dumps(filters), shared)
        return jsonify({'success': True, 'view_id': vid})
    except Exception as e:
        logger.error(f"Failed to save view: {e}")
        return jsonify({'error': 'save_failed'}), 500

@admin_bp.route('/saved-views/<int:view_id>', methods=['DELETE'])
@admin_required
def delete_view(view_id):
    admin_id = session.get('user_id')
    try:
        db.delete_view(admin_id, view_id)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Failed to delete view {view_id}: {e}")
        return jsonify({'error': 'delete_failed'}), 500

@admin_bp.route('/saved-views/<int:view_id>/share', methods=['PATCH'])
@admin_required
def share_view(view_id):
    admin_id = session.get('user_id')
    payload = request.json or {}
    shared = bool(payload.get('shared', True))
    try:
        db.share_view(admin_id, view_id, shared)
        return jsonify({'success': True, 'shared': shared})
    except Exception as e:
        logger.error(f"Failed to share view {view_id}: {e}")
        return jsonify({'error': 'share_failed'}), 500

from services.pinecone_service import get_rag_stats

@admin_bp.route('/rag-status', methods=['GET'])
@admin_required
def rag_status():
    """Return content coverage per category and missing areas + Pinecone Index Stats"""
    try:
        # Get category coverage stats (DB)
        course_id = request.args.get('course_id', 1, type=int)
        stats = db.get_upload_stats_by_category(course_id=course_id)
        categories = []
        for name, data in stats.items():
            categories.append({
                'category': name,
                'video_count': data['video_count'],
                'chunk_count': data['total_chunks'],
                'status': 'ok' if (data['video_count'] and data['total_chunks']) else 'missing'
            })
        
        # Also include categories with zero coverage
        known = set(stats.keys())
        try:
            course_cats = db.get_course_categories(course_id)
            course_cat_names = [c.get('name') for c in course_cats]
        except Exception:
            course_cat_names = []
        for name in course_cat_names:
            if name not in known:
                categories.append({
                    'category': name,
                    'video_count': 0,
                    'chunk_count': 0,
                    'status': 'missing'
                })
        
        # Get Pinecone Index Stats
        rag_stats = get_rag_stats()
        
        return jsonify({
            'categories': categories,
            'index_stats': rag_stats
        })
    except Exception as e:
        return jsonify({'error': 'server_error', 'message': str(e)}), 500

@admin_bp.route('/kpi', methods=['GET'])
@admin_required
def kpi():
    """Role-based KPI endpoint with optional filters"""
    try:
        role = request.args.get('role')  # e.g., 'candidate'
        category = request.args.get('category')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        course_id = request.args.get('course_id', 1, type=int)
        # Use search_sessions to compute scoped KPIs
        sessions, _ = db.search_sessions(
            start_date=start_date,
            end_date=end_date,
            category=category,
            role=role,
            course_id=course_id,
            page=1,
            limit=100000
        )
        
        completed = [s for s in sessions if s.get('status') == 'completed']
        avg_score = round(sum([s['overall_score'] for s in completed if s.get('overall_score') is not None]) / max(1, len([s for s in completed if s.get('overall_score') is not None])), 1) if completed else 0.0
        
        # Calculate scoped stats
        unique_candidates = set(s['user_id'] for s in sessions if s.get('user_id'))
        today_str = datetime.now().strftime('%Y-%m-%d')
        active_today_count = len(set(s['user_id'] for s in sessions if s.get('user_id') and str(s.get('started_at', '')).startswith(today_str)))

        return jsonify({
            'total_sessions': len(sessions),
            'completed_sessions': len(completed),
            'average_score': avg_score,
            'total_candidates': len(unique_candidates),
            'active_today': active_today_count
        })
    except Exception as e:
        return jsonify({'error': 'server_error', 'message': str(e)}), 500

@viewer_bp.route('/kpi', methods=['GET'])
@role_required(['viewer', 'admin'])
def viewer_kpi():
    try:
        role = request.args.get('role')
        category = request.args.get('category')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        course_id = request.args.get('course_id', 1, type=int)
        sessions, _ = db.search_sessions(
            start_date=start_date,
            end_date=end_date,
            category=category,
            role=role,
            course_id=course_id,
            page=1,
            limit=100000
        )
        completed = [s for s in sessions if s.get('status') == 'completed']
        avg_score = round(sum([s['overall_score'] for s in completed if s.get('overall_score') is not None]) / max(1, len([s for s in completed if s.get('overall_score') is not None])), 1) if completed else 0.0
        unique_candidates = set(s['user_id'] for s in sessions if s.get('user_id'))
        today_str = datetime.now().strftime('%Y-%m-%d')
        active_today_count = len(set(s['user_id'] for s in sessions if s.get('user_id') and str(s.get('started_at', '')).startswith(today_str)))
        return jsonify({
            'total_sessions': len(sessions),
            'completed_sessions': len(completed),
            'average_score': avg_score,
            'total_candidates': len(unique_candidates),
            'active_today': active_today_count
        })
    except Exception as e:
        return jsonify({'error': 'server_error', 'message': str(e)}), 500
@admin_bp.route('/sessions/<int:session_id>', methods=['DELETE'])
@admin_required
def delete_session(session_id):
    """Delete a session (admin only)"""
    try:
        db.delete_session(session_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': 'deletion_failed', 'message': str(e)}), 500

@admin_bp.route('/sessions/<int:session_id>/notes', methods=['PUT'])
@admin_required
def update_session_notes_route(session_id):
    """Update session notes"""
    try:
        data = request.json
        notes = data.get('notes')
        
        if notes is None:
            return jsonify({'error': 'missing_notes'}), 400
            
        db.update_session_notes(session_id, notes)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': 'update_failed', 'message': str(e)}), 500

@admin_bp.route('/sessions/search', methods=['GET'])
@admin_required
def search_sessions_route():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    search = request.args.get('search')
    user_id = request.args.get('user_id')
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    min_score = request.args.get('min_score', type=float)
    max_score = request.args.get('max_score', type=float)
    category = request.args.get('category')
    role = request.args.get('role')
    course_id = request.args.get('course_id', 1, type=int)
    
    # Use existing db helper to search sessions
    sessions, total = db.search_sessions(
        search_term=search,
        page=page,
        limit=limit,
        start_date=start_date,
        end_date=end_date,
        min_score=min_score,
        max_score=max_score,
        category=category,
        role=role,
        course_id=course_id
    )
    
    return jsonify({
        'sessions': sessions,
        'pagination': {
            'total': total,
            'page': page,
            'limit': limit,
            'pages': (total + limit - 1) // limit if limit > 0 else 0
        }
    })

@viewer_bp.route('/sessions/search', methods=['GET'])
@role_required(['viewer', 'admin'])
def viewer_search_sessions_route():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    search = request.args.get('search')
    user_id = request.args.get('user_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    min_score = request.args.get('min_score', type=float)
    max_score = request.args.get('max_score', type=float)
    category = request.args.get('category')
    role = request.args.get('role')
    course_id = request.args.get('course_id', 1, type=int)
    sessions, total = db.search_sessions(
        search_term=search,
        page=page,
        limit=limit,
        start_date=start_date,
        end_date=end_date,
        min_score=min_score,
        max_score=max_score,
        category=category,
        role=role,
        course_id=course_id
    )
    return jsonify({
        'sessions': sessions,
        'pagination': {
            'total': total,
            'page': page,
            'limit': limit,
            'pages': (total + limit - 1) // limit if limit > 0 else 0
        }
    })

@viewer_bp.route('/sessions/user/<int:user_id>', methods=['GET'])
@role_required(['viewer', 'admin'])
def viewer_get_user_sessions_route(user_id: int):
    try:
        course_id = request.args.get('course_id', 1, type=int)
        sessions = db.get_user_sessions(user_id, course_id=course_id)
        return jsonify({'sessions': sessions})
    except Exception as e:
        logger.error(f"Failed to get user sessions for viewer: {e}")
        return jsonify({'error': 'server_error'}), 500

@admin_bp.route('/categories', methods=['GET'])
@admin_required
def get_categories_stats_route():
    """Get upload statistics by category"""
    try:
        course_id = request.args.get('course_id', 1, type=int)
        stats = db.get_upload_stats_by_category(course_id=course_id)
        
        # Format for frontend
        categories_list = []
        for category, data in stats.items():
            categories_list.append({
                'name': category,
                'video_count': data['video_count'],
                'chunk_count': data['total_chunks']
            })
            
        return jsonify({
            'categories': categories_list
        })
    except Exception as e:
        logger.error(f"Error getting category stats: {e}")
        return jsonify({'error': str(e)}), 500
