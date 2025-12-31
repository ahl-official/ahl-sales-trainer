## Goal
Implement priorities A–G end-to-end so that the codebase fully satisfies all functional, objection-handling, and testing requirements in `PROJECT_SPECIFICATION_TRAINING_SYSTEM_V3.md`, and keep the spec file itself accurate and up to date.

## Step Plan

### A. Answer-Based RAG In Evaluation (FR-2 Full Completion)
- Add a small helper in `backend/app.py` to:
  - Embed the **user’s answer** using the same OpenAI embeddings model as elsewhere.
  - Query Pinecone with that embedding limited to the relevant category namespaces.
  - Return a joined text snippet of top-k chunks.
- Update `evaluate_answer_internal(session_id, question, user_answer, category)` to:
  - Use this answer-specific RAG context instead of (or in addition to) the current category-level `aggregate_category_content` when building the `evaluation_prompt`.
  - Keep objection vs non-objection prompts intact, only swapping in the new `RELEVANT TRAINING CONTENT`.
- Add/extend tests so evaluation still works when we monkeypatch network calls (fall back path already covered); ensure new helper is invoked without breaking anything.

### B. Content Upload & Master Objection Script (Operational Completion)
- Ensure code path for ingest is correct so that when `Sales_Objections_Master_Script.txt` is uploaded via the admin UI:
  - It is chunked and stored in Pinecone under the proper category namespace.
- In the spec’s **Integration Requirements / Content Upload** section, explicitly mark this as a **manual operational step** and keep the instructions correct.
- Optionally, add a tiny Python helper script (e.g. `tools/upload_master_objection_script.py`) that can be run locally to ingest the script into Pinecone for dev/staging.

### C. Spec-Requested Tests (Objection Handling & Flow)
- Implement tests aligned with the “Testing Requirements” section but adapted to the current architecture:
  - `tests/test_objection_handling.py`:
    - Use the existing `prepare_questions_internal_v3` and `evaluate_answer_internal` indirectly via Flask endpoints.
    - Test that Sales Objections sessions generate questions with `is_objection = True` and that evaluations include `objection_score`, `forbidden_mistakes_made`, and `prescribed_language_used` fields.
  - `tests/test_objection_flow.py`:
    - Use Flask test client to simulate a full Sales Objections session:
      - Start session.
      - Get first question via `/api/training/get-next-question`.
      - Evaluate at least one “good” answer and one “forbidden mistake” answer (with network mocked to avoid real LLM calls).
      - End session and assert that GET `/api/training/report/{session_id}` returns HTML containing objection metrics.
- Keep all network calls for embeddings/LLM mocked in these tests so the suite remains fast and deterministic.

### D. Performance & Logging (NFR-1 Awareness)
- Add simple timing instrumentation around:
  - Question generation (`prepare_questions_internal_v3`).
  - Evaluation (`evaluate_answer_internal`).
  - Report generation (`build_enhanced_report_html`).
- Log durations with the existing logger so we can confirm they are within NFR thresholds during manual runs.
- (Optional) Add a lightweight test that monkeypatches time to assert that the timing code executes, without enforcing strict thresholds in CI.

### E. Database Migration Script & Spec Alignment
- Create `migrations/add_question_system.sql` that reflects the **actual** schema:
  - `question_bank` columns as implemented (session_id, question_text, expected_answer, key_points_json, source, difficulty, position, is_objection, timestamps).
  - `answer_evaluations` columns including objection fields and what_correct/missed/wrong.
  - `messages` extra column `evaluation_data`.
  - Any relevant indexes actually used in code.
- Update the SQL block in `PROJECT_SPECIFICATION_TRAINING_SYSTEM_V3.md` under “1. Database Schema Changes” to match this real migration and mark that block as `[x] Implemented`.

### F. Module / Spec Consistency
- For `question_generator.py` and `answer_evaluator.py` sections in the spec:
  - Decide on minimal wrapper modules that:
    - Expose functions like `generate_questions_from_content` and `evaluate_objection_handling` but internally delegate to `prepare_questions_internal_v3` and `evaluate_answer_internal` to avoid code duplication.
  - Or, if keeping everything in `app.py` is preferred, edit the spec so those sections explicitly state that the functionality is implemented inside `app.py` instead of standalone modules, and mark the deliverables as completed.
- Update the spec checkboxes and wording so it truthfully reflects the actual implementation structure, without promising non-existent files.

### G. Final Test Run & Spec Check
- Run the full backend test suite again (`pytest -q` in `/backend`).
- Sanity-check the trainer frontend manually (or with a basic scripted test) for:
  - Question flow.
  - Real-time feedback.
  - Report display and PDF download.
- Do a final pass over `PROJECT_SPECIFICATION_TRAINING_SYSTEM_V3.md`:
  - Mark completed items (FR-1..FR-6, NFR where covered, testing items where we added tests).
  - Ensure no remaining checkboxes imply unimplemented code.
  - Explicitly note any residual **manual** tasks (e.g., uploading the Master Objection Script, production performance validation) as operational steps, not missing features.

After this plan is approved, I will execute the steps in order A→G, verifying with tests and updating the spec file as part of the same work cycle.