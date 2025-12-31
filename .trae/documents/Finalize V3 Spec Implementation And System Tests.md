## Remaining Work Overview
- Close gaps against the spec: include per-question “what was correct/missed/wrong” in reports; strengthen DB to persist these fields; add robust tests for evaluation fallback and overall flow; minor UX polish on trainer flow remains compliant.

## Changes To Implement
### 1) Database And Persistence
- Extend `answer_evaluations` schema to add: `what_correct TEXT`, `what_missed TEXT`, `what_wrong TEXT`.
- Add safe migration (PRAGMA column check + ALTER TABLE) in `database.initialize()`.
- Update `save_answer_evaluation()` to persist these new fields from the evaluation JSON.

### 2) Report Builder
- Update `build_enhanced_report_html()` to:
  - Render per-question “what_correct/what_missed/what_wrong” if present.
  - Add a small Strengths/Areas to Improve section (top 2–3 items based on scores and those fields) with source references.
  - Keep tailwind-only, PDF-compatible HTML.

### 3) Backend Behavior (Already In Place)
- Question generation v3 with objection scenarios (done).
- Evaluation rubric with penalties/bonus and objection_score (done).
- Adaptive next-question selection (basic) (done).
- Enhanced report auto-generation on GET (done).

### 4) Frontend Trainer Flow
- Confirm the refactor uses question bank and evaluation endpoint (done); optionally speak next question after feedback (leave as-is to avoid overlapping audio; can enable later).

### 5) Tests
- Add `test_evaluate_fallback.py`:
  - Monkeypatch `requests.post` to throw (for both embeddings and chat) to verify endpoint returns a safe default evaluation and persists it.
- Keep `test_report_enhanced.py` (already added) and full suite green.

### 6) Manual System Verification
- Admin uploads `Sales_Objections_Master_Script.txt` under category “Sales Objections”.
- Start a Sales Objections session, answer 2–3 questions, confirm: real-time spoken feedback, objection scoring, enhanced report (HTML) and PDF export.

If you approve, I’ll implement the DB migration + persistence, update the report builder, add the fallback test, run all tests, and summarize verification steps.