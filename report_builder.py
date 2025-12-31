from typing import List, Dict, Optional
import json


def _classify_question_type(text: str) -> str:
    t = (text or '').strip().lower()
    if not t:
        return 'factual'
    starters = ['what', 'when', 'where', 'how much', 'how many']
    if any(t.startswith(s) for s in starters):
        return 'factual'
    if 'steps' in t or t.startswith('how to') or t.startswith('how do i') or 'procedure' in t:
        return 'procedural'
    if 'scenario' in t or 'what if' in t or 'how would you handle' in t:
        return 'scenario'
    return 'procedural'


def _avg(values: List[Optional[float]]) -> Optional[float]:
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return None
    return round(sum(nums) / len(nums), 1)


def build_enhanced_report_html(db, session_id: int) -> str:
    session = db.get_session(session_id)
    user = db.get_user_by_id(session['user_id']) if session else None
    questions = db.get_session_questions(session_id)

    # Map question_id -> evaluation row
    # We will fetch all evaluations by joining in memory using db helper
    # Since there is no dedicated fetch, we infer by reading all from table via existing methods
    # Reuse get_session_questions and then for each question, attempt to find an evaluation via a simple query
    # Implement a tiny local fetch using database connection
    conn = db._get_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM answer_evaluations WHERE session_id = ?', (session_id,))
    eval_rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    eval_by_qid: Dict[int, Dict] = {e['question_id']: e for e in eval_rows}

    # Compute dimension scores
    factual_scores: List[Optional[float]] = []
    procedural_scores: List[Optional[float]] = []
    scenario_scores: List[Optional[float]] = []
    clarity_scores: List[Optional[float]] = []
    objection_scores: List[Optional[float]] = []
    overall_scores: List[Optional[float]] = []

    rows_html = []
    strengths: List[str] = []
    improvements: List[str] = []
    for q in questions:
        qid = q['id']
        qtext = q['question_text']
        exp = q.get('expected_answer') or ''
        src = q.get('source') or ''
        is_obj = bool(q.get('is_objection'))
        ev = eval_by_qid.get(qid)
        user_answer = ev.get('user_answer') if ev else None
        overall = ev.get('overall_score') if ev else None
        clarity = ev.get('clarity') if ev else None
        objection_score = ev.get('objection_score') if ev else None
        what_correct = ev.get('what_correct') if ev else None
        what_missed = ev.get('what_missed') if ev else None
        what_wrong = ev.get('what_wrong') if ev else None
        evidence = ev.get('evidence') if ev else ''

        if overall is not None:
            overall_scores.append(overall)
        if clarity is not None:
            clarity_scores.append(clarity)

        if is_obj:
            if objection_score is not None:
                objection_scores.append(objection_score)
        else:
            qtype = _classify_question_type(qtext)
            if qtype == 'factual' and overall is not None:
                factual_scores.append(overall)
            elif qtype == 'procedural' and overall is not None:
                procedural_scores.append(overall)
            elif qtype == 'scenario' and overall is not None:
                scenario_scores.append(overall)

        detail_html = ''
        if any([what_correct, what_missed, what_wrong, evidence]):
            detail_html = "<div class='mt-2 text-xs text-gray-600 space-y-1'>"
            if what_correct:
                detail_html += f"<div><span class='font-semibold text-green-700'>Correct:</span> {what_correct}</div>"
            if what_missed:
                detail_html += f"<div><span class='font-semibold text-yellow-700'>Missed:</span> {what_missed}</div>"
            if what_wrong:
                detail_html += f"<div><span class='font-semibold text-red-700'>Wrong:</span> {what_wrong}</div>"
            if evidence:
                detail_html += f"<div><span class='font-semibold'>Evidence:</span> {evidence}</div>"
            detail_html += "</div>"

        rows_html.append(f"""
        <tr class='border-t'>
          <td class='p-3 align-top text-sm'>
            <div>{qtext}</div>
            {detail_html}
          </td>
          <td class='p-3 align-top text-sm'>{(user_answer or '—')}</td>
          <td class='p-3 align-top text-sm'>{exp}</td>
          <td class='p-3 align-top text-sm'>{(src or '—')}</td>
          <td class='p-3 align-top text-sm text-center'>{(round(overall,1) if isinstance(overall,(int,float)) else '—')}</td>
        </tr>
        """)

        # Collect strengths/improvements quick bullets
        if isinstance(overall, (int, float)):
            if overall >= 8:
                strengths.append(f"{qtext} — strong ({round(overall,1)}/10){' • ' + src if src else ''}")
            elif overall < 5:
                improvements.append(f"{qtext} — needs work ({round(overall,1)}/10){' • ' + src if src else ''}")

    # Aggregates
    overall_avg = _avg(overall_scores)
    clarity_avg = _avg(clarity_scores)
    factual_avg = _avg(factual_scores)
    procedural_avg = _avg(procedural_scores)
    scenario_avg = _avg(scenario_scores)
    objection_avg = _avg(objection_scores) if 'objection' in (session['category'] or '').lower() else None

    # Build HTML
    user_display = user['username'] if user else 'Candidate'
    cat = session['category'] if session else '—'
    diff = session['difficulty'] if session else '—'

    subs_html = f"""
      <div class='grid grid-cols-1 md:grid-cols-2 gap-4'>
        <div class='p-4 bg-gray-50 rounded border'>
          <div class='text-sm text-gray-600'>Factual Knowledge</div>
          <div class='text-2xl font-bold'>{factual_avg if factual_avg is not None else 'N/A'}/10</div>
        </div>
        <div class='p-4 bg-gray-50 rounded border'>
          <div class='text-sm text-gray-600'>Procedural Understanding</div>
          <div class='text-2xl font-bold'>{procedural_avg if procedural_avg is not None else 'N/A'}/10</div>
        </div>
        <div class='p-4 bg-gray-50 rounded border'>
          <div class='text-sm text-gray-600'>Scenario Handling</div>
          <div class='text-2xl font-bold'>{scenario_avg if scenario_avg is not None else 'N/A'}/10</div>
        </div>
        <div class='p-4 bg-gray-50 rounded border'>
          <div class='text-sm text-gray-600'>Communication Clarity</div>
          <div class='text-2xl font-bold'>{clarity_avg if clarity_avg is not None else 'N/A'}/10</div>
        </div>
      </div>
    """

    objection_block = ''
    if objection_avg is not None:
        objection_block = f"""
          <div class='p-4 bg-blue-50 rounded border border-blue-200'>
            <div class='text-sm text-blue-700'>Objection Handling</div>
            <div class='text-2xl font-bold text-blue-900'>{objection_avg}/10</div>
            <div class='text-sm text-blue-800 mt-1'>This score reflects adherence to prescribed objection-handling methodology.</div>
          </div>
        """

    table_html = """
      <table class='w-full text-left mt-6 border border-gray-200 rounded'>
        <thead class='bg-gray-100 text-gray-700'>
          <tr>
            <th class='p-3 text-sm font-semibold'>Question</th>
            <th class='p-3 text-sm font-semibold'>Your Answer</th>
            <th class='p-3 text-sm font-semibold'>Expected Answer</th>
            <th class='p-3 text-sm font-semibold'>Source</th>
            <th class='p-3 text-sm font-semibold text-center'>Score</th>
          </tr>
        </thead>
        <tbody>
    """ + "".join(rows_html) + """
        </tbody>
      </table>
    """

    strengths_html = ''
    if strengths:
        items = ''.join([f"<li class='list-disc ml-5'>{s}</li>" for s in strengths[:4]])
        strengths_html = f"""
        <div class='p-4 bg-green-50 rounded border border-green-200'>
          <div class='font-semibold text-green-900'>Strengths</div>
          <ul class='mt-1 text-sm text-green-900'>{items}</ul>
        </div>
        """

    improvements_html = ''
    if improvements:
        items = ''.join([f"<li class='list-disc ml-5'>{s}</li>" for s in improvements[:4]])
        improvements_html = f"""
        <div class='p-4 bg-yellow-50 rounded border border-yellow-200'>
          <div class='font-semibold text-yellow-900'>Areas to Improve</div>
          <ul class='mt-1 text-sm text-yellow-900'>{items}</ul>
        </div>
        """

    overall_meta = overall_avg if overall_avg is not None else ''
    html = f"""
      <meta name='overall_score' content='{overall_meta}'>
      <meta name='category' content='{cat}'>
      <div class='space-y-6'>
        <div class='flex items-center justify-between'>
          <h2 class='text-2xl font-bold text-gray-800'>Sales Training Performance Report</h2>
          <div class='text-right'>
            <div class='text-sm text-gray-600'>Candidate</div>
            <div class='font-semibold'>{user_display}</div>
            <div class='text-sm text-gray-600 mt-1'>Category / Difficulty</div>
            <div class='font-semibold'>{cat} / {diff}</div>
          </div>
        </div>
        <div class='p-4 bg-green-50 rounded border border-green-200'>
          <div class='text-sm text-green-700'>Overall Score</div>
          <div class='text-3xl font-extrabold text-green-900'>{overall_avg if overall_avg is not None else 'N/A'}/10</div>
        </div>
        {objection_block}
        {subs_html}
        <div class='grid grid-cols-1 md:grid-cols-2 gap-4'>
          {strengths_html}
          {improvements_html}
        </div>
        <div>
          <h3 class='text-xl font-semibold text-gray-800 mt-4'>Question-by-Question Analysis</h3>
          {table_html}
        </div>
      </div>
    """
    return html

def build_candidate_report_html(db, session_id: int) -> str:
    session = db.get_session(session_id)
    user = db.get_user_by_id(session['user_id']) if session else None
    questions = db.get_session_questions(session_id)
    conn = db._get_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM answer_evaluations WHERE session_id = ?', (session_id,))
    eval_rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    eval_by_qid: Dict[int, Dict] = {e['question_id']: e for e in eval_rows}
    rows_html = []
    for q in questions:
        qid = q['id']
        qtext = q['question_text']
        exp = q.get('expected_answer') or ''
        ev = eval_by_qid.get(qid)
        user_answer = ev.get('user_answer') if ev else None
        rows_html.append(f"""
        <tr class='border-t'>
          <td class='p-3 align-top text-sm'>{qtext}</td>
          <td class='p-3 align-top text-sm'>{(user_answer or '—')}</td>
          <td class='p-3 align-top text-sm'>{exp}</td>
        </tr>
        """)
    user_display = user['username'] if user else 'Candidate'
    cat = session['category'] if session else '—'
    diff = session['difficulty'] if session else '—'
    table_html = """
      <table class='w-full text-left mt-4 border border-gray-200 rounded'>
        <thead class='bg-gray-100 text-gray-700'>
          <tr>
            <th class='p-3 text-sm font-semibold'>Question</th>
            <th class='p-3 text-sm font-semibold'>Your Answer</th>
            <th class='p-3 text-sm font-semibold'>Expected Answer</th>
          </tr>
        </thead>
        <tbody>
    """ + "".join(rows_html) + """
        </tbody>
      </table>
    """
    html = f"""
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
    return html
