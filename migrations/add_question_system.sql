-- Question and evaluation schema aligned with current implementation

CREATE TABLE IF NOT EXISTS question_bank (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    expected_answer TEXT,
    key_points_json TEXT,
    source TEXT,
    difficulty TEXT,
    position INTEGER,
    is_objection INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS answer_evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    user_answer TEXT NOT NULL,
    accuracy REAL,
    completeness REAL,
    clarity REAL,
    tone REAL,
    technique REAL,
    closing REAL,
    overall_score REAL,
    feedback TEXT,
    evidence TEXT,
    objection_score REAL,
    technique_adherence INTEGER,
    what_correct TEXT,
    what_missed TEXT,
    what_wrong TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES question_bank(id) ON DELETE CASCADE
);

ALTER TABLE messages ADD COLUMN evaluation_data TEXT;

CREATE INDEX IF NOT EXISTS idx_question_bank_session_id ON question_bank(session_id);
CREATE INDEX IF NOT EXISTS idx_question_bank_position ON question_bank(position);
CREATE INDEX IF NOT EXISTS idx_answer_evaluations_session_id ON answer_evaluations(session_id);
CREATE INDEX IF NOT EXISTS idx_answer_evaluations_question_id ON answer_evaluations(question_id);

