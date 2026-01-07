from flask import Blueprint, request, jsonify, session
import os
from services.training_service import prepare_questions, evaluate_answer, determine_adaptive_difficulty
from utils.decorators import login_required
from extensions import db
from report_builder import build_enhanced_report_html, build_candidate_report_html
from validators import StartSessionRequest, validate_session_id
from config_logging import get_logger
import re

logger = get_logger('training_routes')

training_bp = Blueprint('training', __name__)

CATEGORIES = [
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

@training_bp.route('/categories', methods=['GET'])
@login_required
def get_categories():
    try:
        stats = db.get_upload_stats_by_category()
        categories_list = []
        for name in CATEGORIES:
            data = stats.get(name, {'video_count': 0, 'total_chunks': 0})
            categories_list.append({
                'name': name,
                'video_count': data.get('video_count') or 0,
                'chunk_count': data.get('total_chunks') or 0
            })
        return jsonify({'categories': categories_list})
    except Exception as e:
        logger.error(f"Failed to get categories: {e}")
        return jsonify({'error': 'server_error'}), 500

@training_bp.route('/deepgram-token', methods=['GET'])
@login_required
def get_deepgram_token():
    try:
        key = os.environ.get('DEEPGRAM_API_KEY', '')
        if not key:
            return jsonify({'error': 'missing_deepgram_key'}), 400
        return jsonify({'key': key})
    except Exception as e:
        logger.error(f"Deepgram token error: {e}")
        return jsonify({'error': 'server_error'}), 500

@training_bp.route('/start', methods=['POST'])
@login_required
def start_session():
    try:
        data = request.json
        req = StartSessionRequest(
            category=data.get('category'),
            difficulty=data.get('difficulty'),
            duration_minutes=int(data.get('duration_minutes', 10))
        )
        req.validate()
        
        # Handle Adaptive Difficulty
        if req.difficulty == 'adaptive':
            req.difficulty = determine_adaptive_difficulty(session['user_id'], req.category)
            logger.info(f"Adaptive difficulty set to {req.difficulty} for user {session['user_id']}")
        
        mode = data.get('mode', 'standard')
        
        session_id = db.create_session(
            session['user_id'],
            req.category,
            req.difficulty,
            req.duration_minutes,
            mode
        )
        
        # Prepare questions in background (or foreground for now)
        # Using the new prepare_questions from service
        prepare_questions(session_id, req.category, req.difficulty, req.duration_minutes)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': 'Session started'
        })
    except ValueError as e:
        return jsonify({'error': 'validation_error', 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Failed to start session: {e}")
        return jsonify({'error': 'server_error', 'message': str(e)}), 500

@training_bp.route('/get-next-question', methods=['POST'])
@login_required
def get_next_question():
    try:
        data = request.json
        session_id = validate_session_id(data.get('session_id'))
        
        # Verify ownership
        if not db.verify_session_owner(session_id, session['user_id']):
            return jsonify({'error': 'unauthorized'}), 403
            
        # Get next question from DB
        question = db.get_next_unanswered_question(session_id)
        
        if not question:
            return jsonify({'done': True})
            
        return jsonify({'done': False, 'question': question})
        
    except ValueError as e:
        return jsonify({'error': 'validation_error', 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Error getting next question: {e}")
        return jsonify({'error': 'server_error'}), 500

@training_bp.route('/evaluate-answer', methods=['POST'])
@login_required
def evaluate_specific_answer():
    try:
        data = request.json
        session_id = validate_session_id(data.get('session_id'))
        question_id = int(data.get('question_id'))
        user_answer = data.get('user_answer') or ''
        
        if not db.verify_session_owner(session_id, session['user_id']):
            return jsonify({'error': 'unauthorized'}), 403
        
        # Find question by id
        questions = db.get_session_questions(session_id)
        question = next((q for q in questions if int(q['id']) == question_id), None)
        if not question:
            return jsonify({'error': 'not_found'}), 404
        
        sess = db.get_session(session_id)
        category = sess['category']
        
        evaluation = evaluate_answer(session_id, question, user_answer, category)
        db.save_answer_evaluation(session_id, question_id, evaluation)
        
        return jsonify({'success': True, 'evaluation': evaluation})
    except ValueError as e:
        return jsonify({'error': 'validation_error', 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Evaluation endpoint failed: {e}")
        return jsonify({'error': 'server_error'}), 500
@training_bp.route('/message', methods=['POST'])
@login_required
def handle_message():
    try:
        data = request.json
        session_id = validate_session_id(data.get('session_id'))
        role = data.get('role')
        content = data.get('content')
        context_source = data.get('context_source') # 'question', 'answer', etc.
        
        if not content:
            return jsonify({'error': 'no_content'}), 400
            
        if not db.verify_session_owner(session_id, session['user_id']):
            return jsonify({'error': 'unauthorized'}), 403
            
        # Save message
        msg_id = db.add_message(session_id, role, content, context_source)
        
        # If user answer, evaluate it
        evaluation = None
        if role == 'user':
            current_q = db.get_next_unanswered_question(session_id)
            if current_q:
                # Get session info for category
                sess = db.get_session(session_id)
                category = sess['category']
                
                # Evaluate
                evaluation = evaluate_answer(session_id, current_q, content, category)
                
                # Save evaluation
                db.save_answer_evaluation(session_id, current_q['id'], evaluation)
        
        return jsonify({
            'success': True,
            'message_id': msg_id,
            'evaluation': evaluation
        })
        
    except ValueError as e:
        return jsonify({'error': 'validation_error', 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Message handling failed: {e}")
        return jsonify({'error': 'server_error'}), 500

@training_bp.route('/autosave', methods=['POST'])
@login_required
def autosave_session():
    try:
        data = request.json
        session_id = data.get('session_id')
        state = data.get('state') # Should be a dict
        
        if not session_id or not state:
            return jsonify({'error': 'missing_data'}), 400
            
        if not db.verify_session_owner(session_id, session['user_id']):
            return jsonify({'error': 'unauthorized'}), 403
            
        import json
        db.save_session_draft(session_id, json.dumps(state))
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Autosave failed: {e}")
        return jsonify({'error': 'autosave_failed'}), 500

@training_bp.route('/onboarding', methods=['GET', 'POST'])
@login_required
def onboarding_status():
    """Get or set onboarding status"""
    try:
        user_id = session.get('user_id')
        if request.method == 'GET':
            status = db.get_user_pref(user_id, 'onboarding_completed')
            return jsonify({'completed': status == 'true'})
        else:
            data = request.json or {}
            completed = data.get('completed', True)
            db.set_user_pref(user_id, 'onboarding_completed', 'true' if completed else 'false')
            return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Onboarding status error: {e}")
        return jsonify({'error': 'server_error'}), 500

@training_bp.route('/resume-check', methods=['GET'])
@login_required
def check_resume_session():
    try:
        # Find latest active session for user
        # We don't have a direct method for this in db, let's query sessions
        # But wait, search_sessions is admin only. 
        # We need a get_user_active_session helper or just query manually
        # Let's rely on db.get_user_sessions but filter for active
        
        user_sessions = db.get_user_sessions(session['user_id'])
        active = [s for s in user_sessions if s.get('status') == 'active']
        
        if not active:
            return jsonify({'has_session': False})
            
        # Get the most recent active session
        latest = active[0] # get_user_sessions orders by started_at DESC
        
        # Check for draft
        draft = db.get_session_draft(latest['id'])
        
        return jsonify({
            'has_session': True,
            'session_id': latest['id'],
            'category': latest['category'],
            'started_at': latest['started_at'],
            'draft': draft # May be None
        })
    except Exception as e:
        logger.error(f"Resume check failed: {e}")
        return jsonify({'error': 'check_failed'}), 500

@training_bp.route('/end', methods=['POST'])
@login_required
def end_session_route():
    try:
        data = request.json
        session_id = validate_session_id(data.get('session_id'))
        
        if not db.verify_session_owner(session_id, session['user_id']):
            return jsonify({'error': 'unauthorized'}), 403
            
        db.complete_session(session_id)
        return jsonify({'success': True})
        
    except ValueError as e:
        return jsonify({'error': 'validation_error', 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"End session failed: {e}")
        return jsonify({'error': 'server_error'}), 500

@training_bp.route('/report/<int:session_id>', methods=['GET'])
@login_required
def get_report(session_id):
    # Verify ownership or allow admin/viewer
    if not db.verify_session_owner(session_id, session['user_id']):
        user = db.get_user_by_id(session['user_id'])
        if not user or user['role'] not in ['admin', 'viewer']:
            return jsonify({'error': 'unauthorized'}), 403
    
    try:
        logger.info(f"Generating report for session {session_id} user {session['user_id']}")
        user = db.get_user_by_id(session['user_id'])
        
        # Determine which report builder to use
        report_html = None
        try:
            if user and user.get('role') == 'admin':
                report_html = build_enhanced_report_html(db, session_id)
            else:
                report_html = build_enhanced_report_html(db, session_id)
        except Exception as build_err:
            logger.error(f"Primary report builder failed: {build_err}", exc_info=True)
            report_html = None

        # Fallback if primary builder returned None or failed
        if not report_html:
            logger.info("Using fallback report generation")
            try:
                sess = db.get_session(session_id)
                qs = db.get_session_questions(session_id)
                conn = db._get_connection()
                cur = conn.cursor()
                cur.execute('SELECT * FROM answer_evaluations WHERE session_id = ?', (session_id,))
                eval_rows = [dict(r) for r in cur.fetchall()]
                conn.close()
                by_qid = {e['question_id']: e for e in eval_rows}
                rows_html = []
                for q in qs:
                    ev = by_qid.get(q['id']) or {}
                    ua = ev.get('user_answer') or '—'
                    # Use expected answer from question bank
                    exp = q.get('expected_answer') or '—'
                    src = q.get('source') or '—'
                    score = ev.get('overall_score')
                    score_str = f"{score}/10" if score is not None else 'N/A'
                    rows_html.append(f"<tr class='border-t'><td class='p-3 align-top text-sm'>{q.get('question_text') or ''}</td><td class='p-3 align-top text-sm'>{ua}</td><td class='p-3 align-top text-sm'>{exp}</td><td class='p-3 align-top text-sm'>{src}</td><td class='p-3 align-top text-sm text-center'>{score_str}</td></tr>")
                
                user_display = (sess or {}).get('username') or 'Candidate'
                cat = (sess or {}).get('category') or '—'
                diff = (sess or {}).get('difficulty') or '—'
                
                table_html = """
                <table class='w-full text-left mt-6 border border-gray-200 rounded table-auto'>
                    <thead class='bg-gray-100 text-gray-700'>
                        <tr>
                            <th class='p-3 text-sm font-semibold'>Question</th>
                            <th class='p-3 text-sm font-semibold'>Your Answer</th>
                            <th class='p-3 text-sm font-semibold'>Expected Answer</th>
                            <th class='p-3 text-sm font-semibold'>Source</th>
                            <th class='p-3 text-sm font-semibold text-center'>Score</th>
                        </tr>
                    </thead>
                    <tbody>""" + "".join(rows_html) + """</tbody>
                </table>
                """
                
                report_html = f"""
                <div class='space-y-4'>
                    <div class='flex items-center justify-between'>
                        <h2 class='text-2xl font-bold text-gray-800'>Session Summary</h2>
                        <div class='text-right'>
                            <div class='text-sm text-gray-600'>Candidate</div>
                            <div class='font-semibold'>{user_display}</div>
                            <div class='text-sm text-gray-600 mt-1'>Category / Difficulty</div>
                            <div class='font-semibold'>{cat} / {diff}</div>
                        </div>
                    </div>
                    <div class='text-sm text-gray-600'>
                        The summary below shows the questions, your answers, and the expected answers.
                    </div>
                    {table_html}
                </div>
                """
            except Exception as fallback_err:
                logger.error(f"Fallback report generation failed: {fallback_err}", exc_info=True)
                # Ultimate fallback - just text
                report_html = "<div class='text-red-500'>Report generation failed. Please contact admin.</div>"
        
        # Extract overall score from meta tag if present
        overall_score = None
        try:
            m = re.search(r"<meta\\s+name=['\"]overall_score['\"]\\s+content=['\"]([^'\"]*)['\"]>", report_html)
            if m:
                val = m.group(1).strip()
                if val:
                    overall_score = float(val)
        except Exception:
            overall_score = None
        
        # Fallback: compute average from evaluations if meta missing
        if overall_score is None:
            try:
                conn = db._get_connection()
                cur = conn.cursor()
                cur.execute("SELECT overall_score FROM answer_evaluations WHERE session_id = ?", (session_id,))
                rows = [r[0] for r in cur.fetchall() if r[0] is not None]
                conn.close()
                if rows:
                    overall_score = round(sum(float(x) for x in rows) / len(rows), 1)
            except Exception:
                overall_score = None
        
        # Persist report and update session score
        try:
            db.save_report(session_id, report_html, overall_score)
            db.complete_session(session_id, overall_score)
        except Exception as e:
            logger.warning(f"Failed to persist report/session score: {e}")
        
        # Also return session data for notes
        session_data = db.get_session(session_id)
        
        return jsonify({
            'success': True,
            'report_html': report_html,
            'session': session_data
        })
    except Exception as e:
        logger.error(f"Report generation failed: {e}", exc_info=True)
        # Final fallback: return a minimal table so candidate never sees failure
        try:
            sess = db.get_session(session_id)
            qs = db.get_session_questions(session_id)
            conn = db._get_connection()
            cur = conn.cursor()
            cur.execute('SELECT * FROM answer_evaluations WHERE session_id = ?', (session_id,))
            eval_rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            by_qid = {e.get('question_id'): e for e in eval_rows}
            rows_html = []
            for q in qs:
                ev = by_qid.get(q.get('id')) or {}
                ua = ev.get('user_answer') or '—'
                exp = q.get('expected_answer') or '—'
                rows_html.append(f"<tr class='border-t'><td class='p-3 align-top text-sm'>{q.get('question_text') or ''}</td><td class='p-3 align-top text-sm'>{ua}</td><td class='p-3 align-top text-sm'>{exp}</td></tr>")
            table_html = """
            <table class='w-full text-left mt-6 border border-gray-200 rounded table-auto'>
              <thead class='bg-gray-100 text-gray-700'>
                <tr>
                  <th class='p-3 text-sm font-semibold'>Question</th>
                  <th class='p-3 text-sm font-semibold'>Your Answer</th>
                  <th class='p-3 text-sm font-semibold'>Expected Answer</th>
                </tr>
              </thead>
              <tbody>""" + "".join(rows_html) + """</tbody>
            </table>
            """
            report_html = f"""
            <div class='space-y-4'>
              <h2 class='text-2xl font-bold text-gray-800'>Session Summary</h2>
              <div class='text-sm text-gray-600'>The summary below shows the questions, your answers, and the expected answers.</div>
              {table_html}
            </div>
            """
            session_data = db.get_session(session_id)
            return jsonify({'success': True, 'report_html': report_html, 'session': session_data})
        except Exception as fe:
            logger.error(f"Ultimate fallback failed: {fe}", exc_info=True)
            return jsonify({'error': 'server_error'}), 500

@training_bp.route('/prepare', methods=['POST'])
@login_required
def prepare_questions_route():
    try:
        data = request.json
        session_id = validate_session_id(data.get('session_id'))
        
        if not db.verify_session_owner(session_id, session['user_id']):
            return jsonify({'error': 'unauthorized'}), 403
        
        sess = db.get_session(session_id)
        if not sess:
            return jsonify({'error': 'not_found'}), 404
        
        result = prepare_questions(
            session_id=session_id,
            category=sess['category'],
            difficulty=sess['difficulty'],
            duration_minutes=int(sess.get('duration_minutes') or 10),
            mode=sess.get('mode', 'standard')
        )
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': 'validation_error', 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Prepare questions failed: {e}")
        return jsonify({'error': 'server_error'}), 500

@training_bp.route('/progress', methods=['GET'])
@login_required
def get_candidate_progress():
    try:
        user_id = session['user_id']
        sessions = db.get_user_sessions(user_id)
        
        completed_sessions = [s for s in sessions if s.get('status') == 'completed']
        count = len(completed_sessions)
        
        high_score_sessions = [s for s in completed_sessions if (s.get('overall_score') or 0) >= 8.0]
        field_ready_sessions = [s for s in completed_sessions if s.get('difficulty') == 'field-ready']
        
        # Check if welcome video watched (using onboarding_completed pref for now)
        video_watched = db.get_user_pref(user_id, 'onboarding_completed') == 'true'
        
        items = [
            {'label': 'Setup Account', 'completed': True},
            {'label': 'Watch Welcome Guide', 'completed': video_watched},
            {'label': 'Complete First Session', 'completed': count >= 1},
            {'label': 'Complete 3 Sessions', 'completed': count >= 3},
            {'label': 'Attempt Field Ready Mode', 'completed': len(field_ready_sessions) > 0},
            {'label': 'Achieve Expert Score (> 8.0)', 'completed': len(high_score_sessions) > 0}
        ]
        
        return jsonify({'items': items})
    except Exception as e:
        logger.error(f"Progress check failed: {e}")
        return jsonify({'error': 'server_error'}), 500
