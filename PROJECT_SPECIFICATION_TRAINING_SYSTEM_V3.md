# 🎯 PROJECT SPECIFICATION: AI SALES TRAINER - INTELLIGENT EVALUATION SYSTEM V3.1

**Project Code:** AHL-TRAINER-V3.1  
**Priority:** P0 - Critical  
**Estimated Effort:** 30-42 hours (1 week)  
**Assigned To:** [Developer Name]  
**Manager:** [Your Name]  
**Created:** December 18, 2025  
**Updated:** December 18, 2025 (Added Objection-Handling Integration)  
**Target Completion:** December 25, 2025

---

## 📋 TABLE OF CONTENTS

1. [Executive Summary](#executive-summary)
2. [Current System Analysis](#current-system-analysis)
3. [Requirements](#requirements)
4. [Special Feature: Objection-Handling Integration](#special-feature-objection-handling-integration)
5. [Technical Architecture](#technical-architecture)
6. [Implementation Plan](#implementation-plan)
7. [Code Changes Required](#code-changes-required)
8. [Testing Requirements](#testing-requirements)
9. [Deployment Checklist](#deployment-checklist)
10. [Success Metrics](#success-metrics)

---

## 📊 EXECUTIVE SUMMARY

### Problem Statement
Current training system asks generic questions without validating answers against training material. Users find it boring and ineffective.

### Solution Overview
Implement an intelligent evaluation system that:
- Generates questions from actual training transcripts
- **Includes company-specific objection-handling scenarios**
- Evaluates answers in real-time against Pinecone knowledge base
- **Tests adherence to prescribed sales techniques**
- Provides immediate feedback after each answer
- Creates detailed reports with evidence-based scoring

### Key Deliverables
1. Question generation system based on training content
2. Real-time answer evaluation with RAG
3. Immediate feedback mechanism
4. Enhanced reporting with question/answer/expected comparison
5. Adaptive difficulty based on performance
6. **🆕 Special objection-handling scenario testing**
7. **🆕 Evaluation against prescribed sales methodology**

### Business Impact
- **Better Learning Outcomes:** Users learn from actual training material
- **Objective Evaluation:** Evidence-based scoring, not guesswork
- **Engagement:** Real-time feedback keeps users engaged
- **Actionable Reports:** Clear areas for improvement with specific references
- **🆕 Consistent Sales Methodology:** All trainees follow company scripts
- **🆕 Realistic Practice:** Test objection handling before real customers

---

## 🔍 CURRENT SYSTEM ANALYSIS

### What Works Now
✅ Speech recognition and synthesis  
✅ Session management  
✅ Pinecone vector storage  
✅ Basic conversation flow  
✅ Report generation

### What's Broken
❌ AI acts as customer (wrong role)  
❌ Questions are generic and boring  
❌ No answer validation against training content  
❌ Scoring is vague guesswork  
❌ Reports lack specific evidence  
❌ No real-time feedback  
❌ **No testing of company-specific sales techniques**  
❌ **No objection-handling practice**

### Current Flow (To Be Replaced)
```
User speaks → AI queries Pinecone → AI asks generic customer question → 
User answers → AI asks another question (no validation) → 
Session ends → Vague report generated
```

### New Flow (To Be Implemented)
```
Pre-Session: AI generates questions from training material →
            🆕 Special handling for objection scenarios →
Session Start: AI asks question as customer →
User answers → AI validates against Pinecone immediately →
            🆕 For objections: Check adherence to prescribed technique →
AI gives real-time feedback →
Track score per question →
Next question (adaptive based on performance) →
Session End: Generate detailed report with Q&A comparison
            🆕 Highlight objection-handling performance
```

---

## 📝 REQUIREMENTS

### Functional Requirements

#### FR-1: Pre-Session Question Generation
**Priority:** P0 - Critical  
**Description:** Before session starts, system must generate 5-10 questions based on actual training transcripts from Pinecone.

**Acceptance Criteria:**
- [x] Retrieve ALL training content for selected category from Pinecone
- [x] Extract key facts, procedures, and scenarios from content
- [x] Generate questions at appropriate difficulty level:
  - **New Joining:** 5-7 factual questions (What, When, How much)
  - **Basic:** 4-5 factual + 2-3 procedural questions (How to, Steps)
  - **Experienced:** 3-4 factual + 3-4 procedural + 2-3 scenario questions
  - **Expert:** 2-3 procedural + 4-5 complex scenario/edge case questions
- [x] Store questions with expected answers and source references
- [x] Each question must have:
  - Question text
  - Expected answer (from training)
  - Key points to check
  - Source video/section reference
  - Difficulty level

**User Story:**
*"As a trainer, I want questions to be based on actual training material so that users are tested on what they were taught, not random topics."*

---

#### FR-2: Real-time Answer Evaluation
**Priority:** P0 - Critical  
**Description:** System must evaluate each user answer against training material immediately and provide feedback.

- **Acceptance Criteria:**
- [x] Capture user's spoken answer
- [x] Get embedding of user's answer
- [x] Query Pinecone for relevant training content (top 5 chunks)
- [x] Compare user answer vs. training content using LLM
- [x] Evaluation must check:
  - **Accuracy:** Is the answer factually correct?
  - **Completeness:** Did they cover key points?
  - **Clarity:** Was it well-articulated?
- [x] Allow paraphrasing (check meaning, not exact words)
- [x] Generate score 0-10 for each answer
- [x] Provide immediate feedback (1-2 sentences)
- [x] Store evaluation results in database

**User Story:**
*"As a user, I want to know immediately after answering if I was correct, so I can learn in real-time rather than waiting until the end."*

---

#### FR-3: Real-time Feedback After Each Answer
**Priority:** P0 - Critical  
**Description:** After each answer, system must provide immediate verbal feedback.

**Acceptance Criteria:**
- [x] If score >= 8/10: Positive feedback ("Excellent! That's correct...")
- [x] If score 5-7/10: Constructive feedback ("Good, but you missed...")
- [x] If score < 5/10: Corrective feedback ("Not quite. The training says...")
- [x] Feedback must be spoken using text-to-speech
- [x] Feedback shown in chat interface
- [x] Feedback stored in session history
- [x] **Important:** Do NOT stop session or ask user to correct - move to next question

**User Story:**
*"As a user, when I give a wrong answer, I want to know what was wrong so I understand my mistake, but I don't want the session to stop."*

---

#### FR-4: Enhanced Report Generation
**Priority:** P0 - Critical  
**Description:** Generate comprehensive report showing question-by-question analysis.

**Acceptance Criteria:**
- [x] Report must include for EACH question:
  - Question asked by AI
  - Answer given by user (exact transcript)
  - Expected answer (from training material)
  - Score (X/10)
  - What was correct
  - What was missed/wrong
  - Source reference (Video name, section)
- [x] Overall category scores:
  - Factual Knowledge: X/10
  - Procedural Understanding: X/10
  - Scenario Handling: X/10
  - Communication Clarity: X/10
  - **🆕 Objection Handling: X/10 (for Sales Objections category)**
- [x] Summary section:
  - Strengths (what they got right)
  - Weaknesses (what they missed)
  - Specific recommendations with video references
- [x] Report must be professional HTML with Tailwind styling

**User Story:**
*"As a manager reviewing reports, I want to see exactly what questions were asked, what the user answered, and what the correct answer should have been, so I can identify specific training gaps."*

---

#### FR-5: Adaptive Question Selection
**Priority:** P1 - High  
**Description:** System should adjust question difficulty based on user performance.

**Acceptance Criteria:**
- [x] Track running average score during session
- [x] If avg >= 8/10: Increase difficulty for remaining questions
- [x] If avg < 5/10: Decrease difficulty or ask simpler related questions
- [x] If user consistently misses a topic: Ask follow-up questions on that topic
- [x] Maximum 10 questions per session (time-based)

**User Story:**
*"As a user, I want questions that match my skill level - not too easy, not too hard - so I stay engaged and challenged."*

---

#### 🆕 FR-6: Special Objection-Handling Integration
**Priority:** P0 - Critical  
**Description:** Sales Objections category must test adherence to company's prescribed objection-handling methodology.

**Acceptance Criteria:**
- [x] Sales Objections category receives special handling
- [ ] Master Objection Script uploaded to Pinecone
- [x] Generate scenario questions from objection script
- [x] Questions test prescribed responses:
  - "I want system to last longer" objection
  - Budget objection (below ₹35,000)
  - "Why not transplant?" objection
  - Closing technique after objections
  - Handling indecisive customers
- [x] Evaluation checks:
  - **Tone:** Calm and authoritative (no apologizing)
  - **Technique:** Following prescribed script
  - **Key Points:** Covering all required points
  - **Closing:** Proper consultation close
- [x] Penalties for common mistakes:
  - Apologizing for pricing: -3 points
  - Arguing with customer: -5 points
  - Over-explaining: -2 points
  - Losing control: -4 points
- [x] Bonus for using exact prescribed language: +2 points
- [x] Report must highlight:
  - Which objections were handled well
  - Which objections need practice
  - Specific script sections to review

**User Story:**
*"As a sales manager, I want to ensure all trainees handle objections using our proven methodology, not making up their own responses."*

**Business Value:**
- Consistent customer experience across all sales consultants
- Higher conversion rates through proven techniques
- Faster onboarding of new sales staff
- Reduced manager intervention

---

### Non-Functional Requirements

#### NFR-1: Performance
- Question generation: < 10 seconds
- Answer evaluation: < 3 seconds
- Report generation: < 5 seconds
- No degradation with multiple concurrent users

#### NFR-2: Accuracy
- Answer evaluation must match human trainer judgment 85%+ of time
- Questions must be directly from training material (verifiable)
- No hallucinated facts in feedback
- **🆕 Objection evaluation matches sales manager judgment 90%+ of time**

#### NFR-3: User Experience
- Feedback must be natural and conversational
- AI voice must remain in character as customer
- No technical jargon in feedback
- Smooth transitions between questions
- **🆕 Objection scenarios feel realistic**

---

## 🎯 SPECIAL FEATURE: OBJECTION-HANDLING INTEGRATION

### Overview
American Hairline has a **Master Objection-Handling Script** that all sales consultants must follow. This section details how to integrate this script into the training system.

### Business Context
The company has specific, proven responses to common customer objections:
1. "I want the system to last longer" → Explain thin vs. thick tradeoff
2. Budget objections → Present two clear options
3. "Why not transplant?" → Explain biological limitations
4. Closing technique → Soft pressure without pushiness
5. Indecisive customers → Remove pressure while maintaining authority

### Training Content: Master Objection Script

**File to Create:** `Sales_Objections_Master_Script.txt`

```txt
=== OBJECTION HANDLING MASTER SCRIPT ===

CATEGORY: Sales Objections
DIFFICULTY: Basic to Expert
SOURCE: American Hairline Official Training Manual

---

PRIORITY QUESTION (Always ask first):

"Sir, before we begin, let me understand one thing clearly —
Is your priority natural appearance or long life of the system?"

This question:
- Anchors the entire consultation
- Exposes unrealistic expectations immediately
- Sets the framework for all following responses

---

OBJECTION 1: "I want the system to last longer"

PRESCRIBED RESPONSE:
"I understand, sir. Everyone wants long life.
But here is the simple truth so you don't get misled anywhere:
A natural-looking system has to be thin.
Thin things don't last long.
If we make it thicker so it lasts longer, it will look more artificial.
So it's always a choice between:
• Natural look, or
• Long life.
You tell me what's more important for you."

PAUSE. Stay quiet. Let them answer.

KEY EVALUATION POINTS:
✅ Acknowledged customer's desire for longevity
✅ Explained thin vs. thick system tradeoff
✅ Presented as a choice, not a limitation
✅ Gave control back to customer
✅ Maintained calm, authoritative tone
❌ Did NOT apologize for system limitations
❌ Did NOT over-explain technical details
❌ Did NOT argue or get defensive

---

OBJECTION 2: "My budget is below ₹35,000"

PRESCRIBED RESPONSE:
"I understand, sir.
But with this budget, we cannot achieve the natural look you are asking for.
High-quality, natural systems require better materials — and that increases the cost.
So here are your two options:
• Increase the budget and get the natural look you want
• Or stay in the budget but accept a system that won't look as natural
Both options are okay — it depends on what you want."

STOP TALKING. Let them choose.

KEY EVALUATION POINTS:
✅ Acknowledged budget constraint
✅ Explained quality-cost relationship clearly
✅ Presented two concrete options
✅ Gave customer the decision
✅ Did not apologize for pricing
❌ Did NOT compare with cheap competitors
❌ Did NOT say "up to you sir" (too passive)
❌ Did NOT lose authority

---

OBJECTION 3: "Why should I spend so much? I might as well do a transplant."

PRESCRIBED RESPONSE:
"Fair point, sir.
But let me explain this in the simplest way:
Your bald area is too large, and your donor area doesn't have enough hair 
to give you the density you're imagining.
No doctor can increase your donor hair — it's biologically limited.
A transplant will cover some area, but not fully.
You will still look thin.
A system gives you:
• Full density
• Immediate results
• Perfect hairline
So the real question is —
Do you want guaranteed density, or are you okay with limited results?"

They will always choose "guaranteed density."

KEY EVALUATION POINTS:
✅ Acknowledged transplant as valid option
✅ Explained biological donor limitations
✅ Listed specific advantages of system
✅ Reframed as density vs. thin hair choice
✅ Maintained expertise and authority
❌ Did NOT dismiss transplants entirely
❌ Did NOT use scare tactics
❌ Did NOT get into argument

---

CLOSING TECHNIQUE (After handling objections):

PRESCRIBED RESPONSE:
"Sir, based on everything you've shared, here's my honest guidance:
The natural-look system is best suited for you. Yes, it has a shorter life, 
but it looks the most undetectable.
If you're okay with this, we can move ahead and customise your unit."

This closing:
- Summarizes their needs
- Acknowledges tradeoffs honestly
- Recommends specific solution
- Applies soft pressure to decide
- Doesn't force but encourages action

KEY EVALUATION POINTS:
✅ Summarized customer's needs
✅ Acknowledged tradeoffs honestly
✅ Made clear recommendation
✅ Asked for decision
✅ Maintained consultative approach
❌ Did NOT say "think about it" (too passive)
❌ Did NOT push too hard

---

OBJECTION 4: "I'll think about it and let you know" (Indecisive customer)

PRESCRIBED RESPONSE:
"Sir, take your time. But remember — your expectations will not change.
You want a natural look.
And for that, you need the right system.
Whenever you're ready, we're here."

This response:
- Gives permission to delay (removes pressure)
- Reminds them of their own stated needs
- Positions you as the solution provider
- Maintains authority without pushiness

KEY EVALUATION POINTS:
✅ Gave permission to take time
✅ Reminded them of expectations
✅ Reinforced solution
✅ Remained available
✅ Removed pressure while maintaining authority
❌ Did NOT beg for decision
❌ Did NOT offer discounts to close now

---

WHAT CONSULTANTS MUST NEVER DO:

❌ Never over-explain (keep it simple)
❌ Never argue with customer
❌ Never apologize for pricing or limitations
❌ Never compare with cheap salons/clinics
❌ Never say "up to you sir, see what you want" (too passive)
❌ Never allow client to control the conversation
❌ Never talk too much — keep answers short and clean
❌ Never show uncertainty or hesitation
❌ Never offer discounts without manager approval

---

EVALUATION RUBRIC FOR OBJECTION HANDLING:

EXCELLENT (9-10):
- Uses prescribed language almost exactly
- Covers all key points
- Maintains calm, authoritative tone
- Closes properly
- Makes no forbidden mistakes

GOOD (7-8):
- Follows prescribed approach
- Covers most key points
- Maintains professional tone
- Minor improvements needed

ACCEPTABLE (5-6):
- General approach correct
- Misses some key points
- Could be more confident
- Needs technique refinement

POOR (3-4):
- Wrong approach
- Misses most key points
- Makes forbidden mistakes
- Needs significant retraining

FAILING (0-2):
- Completely wrong technique
- Apologetic or defensive
- Lost control of conversation
- Must not interact with customers yet
```

### Integration Requirements

#### 1. Content Upload
**Task:** Upload objection script to system  
**Time:** 5 minutes  
**Steps:**
1. Save above content as `Sales_Objections_Master_Script.txt`
2. Login as admin
3. Navigate to Upload page
4. Category: "Sales Objections"
5. Video Name: "Master Objection Handling Script"
6. Upload file
7. System processes and adds to Pinecone

**Status:**  
- [ ] Script uploaded to development  
- [ ] Script uploaded to staging  
- [ ] Script uploaded to production*** End Patch*** 奶头assistant to=functions.apply_patchөнхий ***!

#### 2. Question Generation Logic
**Task:** Generate objection-specific scenario questions  
**Time:** 3 hours  
**Deliverable:** Modified `question_generator.py` with objection scenarios

#### 3. Evaluation Logic
**Task:** Stricter evaluation for objection responses  
**Time:** 2 hours  
**Deliverable:** Modified `answer_evaluator.py` with objection rubric

#### 4. Report Enhancement
**Task:** Highlight objection-handling performance  
**Time:** 1 hour  
**Deliverable:** Enhanced report showing objection scores separately

---

## 🏗️ TECHNICAL ARCHITECTURE

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (trainer.html)                   │
├─────────────────────────────────────────────────────────────┤
│  • Start Session → Prepare Questions                         │
│  • 🆕 Detect if category is Sales Objections               │
│  • Capture User Speech → Send to Backend                     │
│  • Display Real-time Feedback                                │
│  • Show Enhanced Report                                      │
│  • 🆕 Highlight objection-handling scores                   │
└─────────────────────────────────────────────────────────────┘
                            ↓ HTTP/JSON
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND (app.py)                          │
├─────────────────────────────────────────────────────────────┤
│  NEW ENDPOINTS:                                              │
│  • POST /api/training/prepare                                │ [x] Implemented
│  • POST /api/training/evaluate-answer                        │ [x] Implemented
│  • POST /api/training/get-next-question                      │ [x] Implemented
│                                                              │
│  MODIFIED ENDPOINTS:                                         │
│  • POST /api/training/start (add question prep)              │ [x] Implemented
│  • POST /api/training/message (add evaluation)               │ [x] Implemented
│  • GET  /api/training/report (enhanced format)               │ [x] Implemented
│                                                              │
│  🆕 NEW MODULES:                                            │
│  • question_generator.py (objection scenarios)               │ [x] Implemented as wrapper over app.py
│  • answer_evaluator.py (objection rubric)                    │ [x] Implemented as wrapper over app.py
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    DATABASE (SQLite)                         │
├─────────────────────────────────────────────────────────────┤
│  NEW TABLES:                                                 │
│  • question_bank (pre-generated questions)                   │
│  • answer_evaluations (per-answer scores)                    │
│                                                              │
│  MODIFIED TABLES:                                            │
│  • messages (add evaluation_data JSON field)                 │
│  • sessions (add question_ids array field)                   │ (handled via question_bank linkage)
│                                                              │
│  🆕 NEW FIELDS:                                              │
│  • answer_evaluations.objection_score (0-10)                 │ [x]
│  • answer_evaluations.technique_adherence (boolean)          │ [x]
│  • answer_evaluations.what_correct/what_missed/what_wrong     │ [x]
└─────────────────────────────────────────────────────────────┘
**Status:**
- [x] `question_bank` table created
- [x] `answer_evaluations` table created
- [x] `messages` table extended with evaluation_data JSON
- [x] `sessions` table: question linkage via `question_bank` (no array needed)
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                 EXTERNAL SERVICES                            │
├─────────────────────────────────────────────────────────────┤
│  • Pinecone (training content retrieval)                     │
│    🆕 Contains Master Objection Script                      │
│  • OpenAI (embeddings)                                       │
│  • OpenRouter (LLM for questions & evaluation)               │
│    🆕 Enhanced prompts for objection evaluation             │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

#### Phase 1: Question Preparation (Enhanced)
```python
User clicks "Start Session" with category "Sales Objections"
    ↓
Frontend: POST /api/training/start {category, difficulty, duration}
    ↓
Backend: prepare_questions(category, difficulty)
    ↓
    1. Query Pinecone for ALL content in category
    2. 🆕 IF category contains "objection":
       - Load objection-specific scenarios
       - Mix with content-based questions
    3. Send to LLM: "Generate 5-10 questions from this content"
    4. Parse LLM response into structured questions
    5. Store in question_bank table
    6. Return question_ids to frontend
    ↓
Frontend: Start conversation with first question
```

#### Phase 2: Answer Evaluation (Enhanced)
```python
User speaks answer to objection scenario
    ↓
Frontend: POST /api/training/message {session_id, content: user_answer}
    ↓
Backend: evaluate_answer(question_id, user_answer, session_id)
    ↓
    1. Get question details and expected answer
    2. Get embedding of user's answer
    3. Query Pinecone for relevant training content
    4. 🆕 IF question_type == "objection_scenario":
       - Use stricter evaluation rubric
       - Check for forbidden mistakes
       - Award bonus for prescribed language
    5. Send to LLM: "Evaluate this answer vs. training content"
    6. Parse evaluation (score, feedback, what's right/wrong)
    7. Store in answer_evaluations table
    8. Generate immediate feedback message
    9. Return feedback to frontend
    ↓
Frontend: Display & speak feedback
    ↓
Frontend: Request next question
    ↓
Backend: Select next question (adaptive based on performance)
    ↓
Continue until time expires or questions exhausted
```

#### Phase 3: Report Generation (Enhanced)
```python
Session ends
    ↓
Frontend: GET /api/training/report/{session_id}
    ↓
Backend: generate_enhanced_report(session_id)
    ↓
    1. Retrieve all questions asked
    2. Retrieve all user answers
    3. Retrieve all evaluations
    4. 🆕 IF category contains "objection":
       - Calculate objection-handling score separately
       - List which objections handled well
       - List which objections need practice
       - Reference specific script sections
    5. Format as structured HTML report
    6. Calculate overall scores
    7. Generate recommendations
    8. Store report in database
    9. Return to frontend
    ↓
Frontend: Display report with Q&A comparison
         🆕 Highlight objection-handling performance
```

---

## 🔧 IMPLEMENTATION PLAN

### Week 1: Core Implementation (30-42 hours)

#### **Day 1: Database & Content Preparation (6 hours)**

**Morning (3 hours):**
1. Create database migration script (1 hour)
2. Run migration on development database (30 min)
3. Test new tables and fields (30 min)
4. Prepare Master Objection Script file (1 hour)

**Afternoon (3 hours):**
5. Upload objection script to system (15 min)
6. Verify content in Pinecone (15 min)
7. Test retrieval of objection content (30 min)
8. Setup question generation skeleton (2 hours)

**Deliverables:**
- ✅ New database tables created
- ✅ Objection script uploaded to Pinecone
- ✅ Question generator file structure ready

---

#### **Day 2: Question Generation System (8 hours)**

**Morning (4 hours):**
1. Implement base question generator (2 hours)
2. Add objection-specific question generator (2 hours)

**Afternoon (4 hours):**
3. Implement question mixing logic (1 hour)
4. Add difficulty-based question selection (2 hours)
5. Write unit tests for question generation (1 hour)

**Deliverables:**
- ✅ `question_generator.py` complete
- ✅ Objection scenarios integrated
- ✅ Unit tests passing

**Code Files:**
- `question_generator.py` (complete)
- `test_question_generator.py` (unit tests)

---

#### **Day 3: Answer Evaluation System (8 hours)**

**Morning (4 hours):**
1. Implement base answer evaluator (2 hours)
2. Add RAG-based evaluation (2 hours)

**Afternoon (4 hours):**
3. Implement objection-specific evaluator (2 hours)
4. Add forbidden mistake detection (1 hour)
5. Write unit tests for evaluation (1 hour)

**Deliverables:**
- ✅ `answer_evaluator.py` complete
- ✅ Objection rubric implemented
- ✅ Unit tests passing

**Code Files:**
- `answer_evaluator.py` (complete)
- `test_answer_evaluator.py` (unit tests)

---

#### **Day 4: Backend Integration (8 hours)**

**Morning (4 hours):**
1. Add new API endpoints to app.py (2 hours)
2. Integrate question generator (1 hour)
3. Integrate answer evaluator (1 hour)

**Afternoon (4 hours):**
4. Add helper functions (1 hour)
5. Update existing endpoints (2 hours)
6. Write integration tests (1 hour)

**Deliverables:**
- ✅ All API endpoints working
- ✅ Question preparation functional
- ✅ Answer evaluation functional
- ✅ Integration tests passing

---

#### **Day 5: Frontend Updates & Testing (10 hours)**

**Morning (5 hours):**
1. Update trainer.html conversation flow (3 hours)
2. Add real-time feedback display (1 hour)
3. Add progress indicators (1 hour)

**Afternoon (5 hours):**
4. Implement enhanced report generation (3 hours)
5. Test complete user flow (1 hour)
6. Fix bugs found during testing (1 hour)

**Deliverables:**
- ✅ Frontend conversation flow updated
- ✅ Real-time feedback working
- ✅ Enhanced reports displaying correctly
- ✅ All bugs fixed

---

### Week 2: Enhancements (Optional - 12-16 hours)

#### **Adaptive Difficulty (6 hours)**
- Implement performance tracking
- Dynamic difficulty adjustment
- Topic-based question selection

#### **Enhanced Reporting (4 hours)**
- Add charts and visualizations
- Progress tracking over multiple sessions
- Comparison with other users

#### **Admin UI (6 hours)**
- Question bank management
- Edit/approve generated questions
- View question effectiveness metrics

---

## 💻 CODE CHANGES REQUIRED

### 1. Database Schema Changes

**File:** `migrations/add_question_system.sql`

```sql
-- Actual schema used by the system
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
```

**Status:**  
- [x] Migration file created and matches runtime schema

---

### 2. Question Generator with Objection Scenarios

**File:** `question_generator.py` (NEW FILE - Complete Implementation)

```python
"""
Question Generation System
Generates intelligent questions from training transcripts
SPECIAL HANDLING for Sales Objections category
"""

import json
import os
import requests
from typing import List, Dict
from config_logging import get_logger

logger = get_logger('question_generator')

OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')


def get_question_count(difficulty: str) -> int:
    """Determine how many questions to generate based on difficulty"""
    counts = {
        'new-joining': 6,  # 6 factual questions
        'basic': 7,         # 5 factual + 2 procedural
        'experienced': 9,   # 4 factual + 3 procedural + 2 scenarios
        'expert': 10        # 3 procedural + 5 complex scenarios + 2 edge cases
    }
    return counts.get(difficulty, 7)


def get_question_distribution(difficulty: str) -> Dict:
    """Get distribution of question types based on difficulty"""
    distributions = {
        'new-joining': {
            'factual': 6,
            'procedural': 0,
            'scenario': 0
        },
        'basic': {
            'factual': 5,
            'procedural': 2,
            'scenario': 0
        },
        'experienced': {
            'factual': 4,
            'procedural': 3,
            'scenario': 2
        },
        'expert': {
            'factual': 2,
            'procedural': 3,
            'scenario': 5
        }
    }
    return distributions.get(difficulty, distributions['basic'])


def generate_objection_scenarios(difficulty: str) -> List[Dict]:
    """
    Generate objection-handling scenario questions
    Based on Master Objection Script
    """
    
    # Base objection scenarios
    objection_scenarios = {
        'basic': [
            {
                'question': 'A customer says "I want the system to last longer, not just look natural." How do you respond?',
                'type': 'objection_scenario',
                'expected_answer': 'I understand, sir. Everyone wants long life. But here is the simple truth: A natural-looking system has to be thin. Thin things don\'t last long. If we make it thicker so it lasts longer, it will look more artificial. So it\'s always a choice between natural look or long life. You tell me what\'s more important for you.',
                'key_points': [
                    'acknowledge desire for longevity',
                    'explain thin vs thick tradeoff',
                    'present as a choice',
                    'give control back to customer',
                    'calm authoritative tone'
                ],
                'forbidden_mistakes': [
                    'apologizing for limitations',
                    'over-explaining technical details',
                    'arguing or being defensive'
                ],
                'source': 'Master Objection Handling Script - Objection 1',
                'is_objection': True
            },
            {
                'question': 'Customer\'s budget is ₹30,000 but they want a natural look. Walk me through your response.',
                'type': 'objection_scenario',
                'expected_answer': 'I understand, sir. But with this budget, we cannot achieve the natural look you are asking for. High-quality, natural systems require better materials — and that increases the cost. So here are your two options: Increase the budget and get the natural look you want, or stay in the budget but accept a system that won\'t look as natural. Both options are okay — it depends on what you want.',
                'key_points': [
                    'acknowledge budget constraint',
                    'explain quality-cost relationship',
                    'present two concrete options',
                    'give customer the decision',
                    'no apologizing for pricing'
                ],
                'forbidden_mistakes': [
                    'comparing with cheap competitors',
                    'saying "up to you sir" (too passive)',
                    'losing authority'
                ],
                'source': 'Master Objection Handling Script - Objection 2',
                'is_objection': True
            }
        ],
        'experienced': [
            {
                'question': 'A customer challenges you: "Why should I spend so much? I\'ll just do a transplant instead." Handle this objection.',
                'type': 'objection_scenario',
                'expected_answer': 'Fair point, sir. But let me explain this in the simplest way: Your bald area is too large, and your donor area doesn\'t have enough hair to give you the density you\'re imagining. No doctor can increase your donor hair — it\'s biologically limited. A transplant will cover some area, but not fully. You will still look thin. A system gives you full density, immediate results, and perfect hairline. So the real question is — do you want guaranteed density, or are you okay with limited results?',
                'key_points': [
                    'acknowledge transplant as valid option',
                    'explain biological donor limitations',
                    'list specific system advantages',
                    'reframe as density vs thin choice',
                    'maintain expertise and authority'
                ],
                'forbidden_mistakes': [
                    'dismissing transplants entirely',
                    'using scare tactics',
                    'getting into argument'
                ],
                'source': 'Master Objection Handling Script - Objection 3',
                'is_objection': True
            },
            {
                'question': 'You\'ve handled the main objections. Now close the consultation. What do you say?',
                'type': 'objection_scenario',
                'expected_answer': 'Sir, based on everything you\'ve shared, here\'s my honest guidance: The natural-look system is best suited for you. Yes, it has a shorter life, but it looks the most undetectable. If you\'re okay with this, we can move ahead and customise your unit.',
                'key_points': [
                    'summarize customer needs',
                    'acknowledge tradeoffs honestly',
                    'make clear recommendation',
                    'ask for decision',
                    'soft pressure without forcing'
                ],
                'forbidden_mistakes': [
                    'saying "think about it" (too passive)',
                    'pushing too hard',
                    'offering discounts without approval'
                ],
                'source': 'Master Objection Handling Script - Closing Technique',
                'is_objection': True
            },
            {
                'question': 'Before discussing anything, what\'s the first question you should ask the customer?',
                'type': 'procedural',
                'expected_answer': 'Sir, before we begin, let me understand one thing clearly — Is your priority natural appearance or long life of the system?',
                'key_points': [
                    'priority question first',
                    'natural look vs longevity',
                    'anchors consultation',
                    'exposes unrealistic expectations'
                ],
                'forbidden_mistakes': [
                    'skipping this question',
                    'asking too many questions at once'
                ],
                'source': 'Master Objection Handling Script - Priority Question',
                'is_objection': True
            }
        ],
        'expert': [
            {
                'question': 'A customer is being indecisive and says "I\'ll think about it and let you know." How do you handle this without being pushy?',
                'type': 'objection_scenario',
                'expected_answer': 'Sir, take your time. But remember — your expectations will not change. You want a natural look. And for that, you need the right system. Whenever you\'re ready, we\'re here.',
                'key_points': [
                    'give permission to take time',
                    'remind them of their expectations',
                    'reinforce solution positioning',
                    'remain available',
                    'remove pressure while maintaining authority'
                ],
                'forbidden_mistakes': [
                    'begging for decision',
                    'offering discounts to close now',
                    'showing desperation'
                ],
                'source': 'Master Objection Handling Script - Objection 4',
                'is_objection': True
            },
            {
                'question': 'A customer keeps asking "Can you make it thicker AND natural looking?" They don\'t understand the tradeoff. How do you handle this persistence?',
                'type': 'objection_scenario',
                'expected_answer': 'I understand you want both, sir. But let me be very clear: This is a physical limitation, not our limitation. Thin material looks natural because it mimics real skin. Thick material looks artificial because it doesn\'t bend and move like skin. This is true everywhere, not just at our clinic. So the choice is: natural look with shorter life, or artificial look with longer life. Which matters more to you?',
                'key_points': [
                    'stay calm despite persistence',
                    'explain physical limitation clearly',
                    'emphasize it\'s universal not company-specific',
                    'force them to choose',
                    'maintain authority'
                ],
                'forbidden_mistakes': [
                    'getting frustrated',
                    'over-explaining repeatedly',
                    'giving in to unrealistic demands'
                ],
                'source': 'Master Objection Handling Script - Advanced Techniques',
                'is_objection': True
            }
        ]
    }
    
    # Get scenarios for this difficulty level
    scenarios = objection_scenarios.get(difficulty, objection_scenarios['basic'])
    
    # Add difficulty level to each question
    for q in scenarios:
        q['difficulty'] = difficulty
    
    return scenarios


def generate_questions_from_content(
    content: str,
    category: str,
    difficulty: str,
    num_questions: int
) -> List[Dict]:
    """
    Generate questions from training content using LLM
    SPECIAL HANDLING for Sales Objections category
    """
    
    # SPECIAL: If category contains "objection", include scenario questions
    if 'objection' in category.lower():
        logger.info(f"Detected Sales Objections category - using special handling")
        
        # Get objection-specific scenarios
        objection_questions = generate_objection_scenarios(difficulty)
        
        # Mix with content-based questions
        num_from_content = max(2, num_questions - len(objection_questions))
        
        logger.info(f"Generating {len(objection_questions)} objection scenarios + {num_from_content} content-based questions")
        
        # Generate remaining questions from content
        content_questions = generate_questions_from_llm(
            content, category, difficulty, num_from_content
        )
        
        # Combine both - objection scenarios first
        all_questions = objection_questions + content_questions
        return all_questions[:num_questions]
    
    # For other categories, use normal generation
    else:
        return generate_questions_from_llm(content, category, difficulty, num_questions)


def generate_questions_from_llm(
    content: str,
    category: str,
    difficulty: str,
    num_questions: int
) -> List[Dict]:
    """
    Generate questions from training content using LLM
    Standard generation for non-objection categories
    """
    
    distribution = get_question_distribution(difficulty)
    
    system_prompt = f"""You are an expert sales training coach creating exam questions.

TRAINING MATERIAL:
{content[:8000]}  # Limit to avoid token limits

TASK: Generate exactly {num_questions} questions to test knowledge of "{category}" based ONLY on the training material above.

QUESTION TYPES NEEDED:
- Factual: {distribution['factual']} questions (What, When, How much, How many)
- Procedural: {distribution['procedural']} questions (What are the steps, How do you, Walk me through)
- Scenario: {distribution['scenario']} questions (What if, How would you handle, What would you do if)

RULES:
1. Questions must be answerable from the training material
2. For each question, identify the expected answer from the material
3. For each question, list 3-5 key points that should be in a good answer
4. Include source reference (which video/section)
5. Make questions natural as if a customer is asking
6. Difficulty: {difficulty}

OUTPUT FORMAT (JSON):
{{
  "questions": [
    {{
      "question": "How long does a Pre Consultation usually take at American Hairline?",
      "type": "factual",
      "expected_answer": "A Pre Consultation typically takes 10-15 minutes, though it can extend to 20 minutes for more complex cases where detailed assessment is needed.",
      "key_points": [
        "10-15 minutes duration",
        "Can extend to 20 minutes",
        "Quick yet thorough",
        "Sets expectations for full consultation"
      ],
      "source": "Video 1 - Pre Consultation Overview, 2:34-3:12",
      "difficulty": "{difficulty}",
      "is_objection": false
    }}
  ]
}}"""

    try:
        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'openai/gpt-4o',
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': f'Generate {num_questions} exam questions for {category} at {difficulty} level.'}
                ],
                'temperature': 0.7,
                'max_tokens': 3000
            },
            timeout=30
        )
        
        response.raise_for_status()
        result = response.json()
        
        content_response = result['choices'][0]['message']['content']
        
        # Parse JSON response
        # Handle both markdown code blocks and raw JSON
        if '```json' in content_response:
            content_response = content_response.split('```json')[1].split('```')[0]
        elif '```' in content_response:
            content_response = content_response.split('```')[1].split('```')[0]
        
        questions_data = json.loads(content_response.strip())
        questions = questions_data.get('questions', [])
        
        logger.info(f"Generated {len(questions)} questions for {category} at {difficulty} level")
        
        return questions
        
    except Exception as e:
        logger.error(f"Question generation failed: {e}", exc_info=True)
        # Return fallback generic questions
        return generate_fallback_questions(category, num_questions, difficulty)


def generate_fallback_questions(category: str, num_questions: int, difficulty: str) -> List[Dict]:
    """Generate basic fallback questions if LLM fails"""
    fallback = [
        {
            'question': f"What are the main steps in {category}?",
            'type': 'procedural',
            'expected_answer': f"The main steps vary based on training material for {category}",
            'key_points': ['process', 'steps', 'procedure'],
            'source': 'Training material',
            'difficulty': difficulty,
            'is_objection': False
        },
        {
            'question': f"How long does {category} typically take?",
            'type': 'factual',
            'expected_answer': "Duration varies based on situation",
            'key_points': ['timing', 'duration'],
            'source': 'Training material',
            'difficulty': difficulty,
            'is_objection': False
        }
    ]
    
    return fallback[:num_questions]
```

---

### 3. Answer Evaluator with Objection Rubric

**File:** `answer_evaluator.py` (NEW FILE - Complete Implementation)

```python
"""
Answer Evaluation System
Evaluates user answers against training material using RAG
SPECIAL HANDLING for objection scenarios
"""

import json
import os
import requests
from typing import Dict
from config_logging import get_logger

logger = get_logger('answer_evaluator')

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')


def evaluate_answer_with_rag(
    question: Dict,
    user_answer: str,
    category: str
) -> Dict:
    """
    Evaluate user's answer against training material
    Routes to appropriate evaluator based on question type
    """
    
    # Check if this is an objection scenario
    is_objection = question.get('is_objection', False) or question.get('question_type') == 'objection_scenario'
    
    if is_objection:
        logger.info("Using objection-specific evaluation")
        return evaluate_objection_handling(question, user_answer, category)
    else:
        logger.info("Using standard evaluation")
        return evaluate_standard_answer(question, user_answer, category)


def evaluate_objection_handling(
    question: Dict,
    user_answer: str,
    category: str
) -> Dict:
    """
    Special evaluation for objection-handling scenarios
    Stricter on following prescribed techniques
    """
    
    # Get embedding and training content (same as standard)
    training_content = get_training_content(user_answer, category)
    
    # Get forbidden mistakes list
    forbidden_mistakes = question.get('forbidden_mistakes', [])
    forbidden_str = '\n'.join([f"  ❌ {mistake}" for mistake in forbidden_mistakes])
    
    evaluation_prompt = f"""You are evaluating a sales trainee's objection-handling response.
This is STRICT evaluation against company's PRESCRIBED methodology.

OBJECTION SCENARIO:
{question['question_text']}

PRESCRIBED RESPONSE (from company training):
{question['expected_answer']}

KEY POINTS TO CHECK:
{json.dumps(question['key_points'], indent=2)}

FORBIDDEN MISTAKES (automatic penalties):
{forbidden_str}

RELEVANT TRAINING CONTENT:
{training_content[:2000]}

USER'S ACTUAL RESPONSE:
"{user_answer}"

EVALUATE SPECIFICALLY:

1. TONE (0-10): Did they stay calm and authoritative? No apologizing?
2. TECHNIQUE (0-10): Did they use the prescribed technique from training?
3. KEY POINTS (0-10): How many required key points did they cover?
4. CLOSING (0-10): Did they give customer a choice or close properly?

PENALTIES (deduct from overall score):
- Apologized for pricing/limitations → -3 points
- Argued with customer → -5 points
- Over-explained unnecessarily → -2 points
- Lost control of conversation → -4 points
- Made any forbidden mistake → -2 points each

BONUS:
- Used exact prescribed language → +2 points
- Covered ALL key points → +1 point

SCORING GUIDE:
- 9-10: Perfect objection handling, ready for customers
- 7-8: Good, minor refinements needed
- 5-6: Acceptable but needs significant technique work
- 3-4: Poor, requires retraining
- 0-2: Failing, must not interact with customers yet

IMPORTANT:
- Be STRICT on following prescribed methodology
- Allow paraphrasing only if meaning is identical
- Check for forbidden mistakes carefully
- This is about company standards, not creativity

OUTPUT FORMAT (JSON):
{{
  "tone": 8.0,
  "technique": 7.0,
  "key_points_covered": 6.0,
  "closing": 9.0,
  "overall_score": 7.5,
  "what_correct": "Used calm tone, explained tradeoff, gave customer choice",
  "what_missed": "Did not ask priority question first, missed 'biological limitation' point",
  "what_wrong": null,
  "forbidden_mistakes_made": [],
  "prescribed_language_used": false,
  "feedback": "Good objection handling! You stayed calm and explained the tradeoff well. Next time, start by asking about their priority between natural look and longevity.",
  "evidence_from_training": "Quote from Master Objection Script showing correct approach",
  "accuracy": 8.0,
  "completeness": 6.0,
  "clarity": 9.0
}}"""

    try:
        eval_response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'openai/gpt-4o',
                'messages': [
                    {'role': 'system', 'content': evaluation_prompt},
                    {'role': 'user', 'content': 'Evaluate this objection-handling response strictly but fairly.'}
                ],
                'temperature': 0.3,  # Lower temperature for consistent evaluation
                'max_tokens': 800
            },
            timeout=30
        )
        
        eval_response.raise_for_status()
        result = eval_response.json()
        
        content = result['choices'][0]['message']['content']
        
        # Parse JSON
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0]
        elif '```' in content:
            content = content.split('```')[1].split('```')[0]
        
        evaluation = json.loads(content.strip())
        
        # Ensure all required fields exist
        if 'accuracy' not in evaluation:
            evaluation['accuracy'] = evaluation.get('technique', 7.0)
        if 'completeness' not in evaluation:
            evaluation['completeness'] = evaluation.get('key_points_covered', 7.0)
        if 'clarity' not in evaluation:
            evaluation['clarity'] = evaluation.get('tone', 7.0)
        
        # Add training content to evaluation for report
        evaluation['training_content'] = [training_content]
        evaluation['is_objection'] = True
        
        logger.info(f"Objection evaluation complete: {evaluation['overall_score']}/10")
        
        return evaluation
        
    except Exception as e:
        logger.error(f"Objection evaluation failed: {e}", exc_info=True)
        return generate_fallback_evaluation(user_answer, question)


def evaluate_standard_answer(
    question: Dict,
    user_answer: str,
    category: str
) -> Dict:
    """
    Standard evaluation for non-objection questions
    """
    
    # Get training content
    training_content = get_training_content(user_answer, category)
    
    evaluation_prompt = f"""You are a strict but fair sales training evaluator.

QUESTION ASKED:
{question['question_text']}

EXPECTED ANSWER (from training material):
{question['expected_answer']}

KEY POINTS TO CHECK:
{json.dumps(question['key_points'], indent=2)}

RELEVANT TRAINING MATERIAL:
{training_content[:2000]}

USER'S ACTUAL ANSWER:
"{user_answer}"

EVALUATE THE USER'S ANSWER:

SCORING CRITERIA:
1. Accuracy (0-10): Is the answer factually correct?
2. Completeness (0-10): Did they mention the key points?
3. Clarity (0-10): Was it clear and well-articulated?

IMPORTANT RULES:
- Allow paraphrasing (they don't need exact words)
- Check meaning, not exact phrasing
- Be fair but strict on facts
- If they say opposite of training → score 0-2
- If they miss key points → deduct accordingly

OUTPUT FORMAT (JSON):
{{
  "accuracy": 8.0,
  "completeness": 6.0,
  "clarity": 9.0,
  "overall_score": 7.7,
  "what_correct": "Correctly mentioned X and Y from training",
  "what_missed": "Did not mention Z which is a key point",
  "what_wrong": null,
  "feedback": "Good answer! You got the main points right, but you could improve by also mentioning Z.",
  "evidence_from_training": "Quote from training material that proves what's correct"
}}"""

    try:
        eval_response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'openai/gpt-4o',
                'messages': [
                    {'role': 'system', 'content': evaluation_prompt},
                    {'role': 'user', 'content': 'Evaluate this answer strictly but fairly.'}
                ],
                'temperature': 0.3,
                'max_tokens': 800
            },
            timeout=30
        )
        
        eval_response.raise_for_status()
        result = eval_response.json()
        
        content = result['choices'][0]['message']['content']
        
        # Parse JSON
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0]
        elif '```' in content:
            content = content.split('```')[1].split('```')[0]
        
        evaluation = json.loads(content.strip())
        
        # Add training content to evaluation for report
        evaluation['training_content'] = [training_content]
        evaluation['is_objection'] = False
        
        logger.info(f"Standard evaluation complete: {evaluation['overall_score']}/10")
        
        return evaluation
        
    except Exception as e:
        logger.error(f"Standard evaluation failed: {e}", exc_info=True)
        return generate_fallback_evaluation(user_answer, question)


def get_training_content(user_answer: str, category: str) -> str:
    """
    Get relevant training content from Pinecone
    """
    try:
        # Get embedding of user's answer
        embed_response = requests.post(
            'https://api.openai.com/v1/embeddings',
            headers={'Authorization': f'Bearer {OPENAI_API_KEY}'},
            json={
                'model': 'text-embedding-3-small',
                'input': user_answer
            },
            timeout=10
        )
        embed_response.raise_for_status()
        embedding = embed_response.json()['data'][0]['embedding']
        
        # Query Pinecone for relevant training content
        from pinecone import Pinecone
        pc = Pinecone(api_key=os.environ.get('PINECONE_API_KEY'))
        index = pc.Index(host=os.environ.get('PINECONE_INDEX_HOST'))
        
        # Query with category filter
        results = index.query(
            vector=embedding,
            top_k=5,
            include_metadata=True,
            filter={'category': category}
        )
        
        # Extract training content
        training_chunks = [
            match['metadata'].get('text', '')
            for match in results.get('matches', [])
            if match.get('metadata')
        ]
        
        training_content = '\n\n'.join(training_chunks)
        return training_content
        
    except Exception as e:
        logger.error(f"Failed to get training content: {e}")
        return ""


def generate_fallback_evaluation(user_answer: str, question: Dict) -> Dict:
    """Generate basic evaluation if LLM fails"""
    # Simple length-based scoring as fallback
    word_count = len(user_answer.split())
    
    if word_count < 5:
        score = 3.0
        feedback = "Your answer was too brief. Please provide more detail."
    elif word_count < 15:
        score = 6.0
        feedback = "Good start, but could be more complete."
    else:
        score = 7.0
        feedback = "Good answer with appropriate detail."
    
    return {
        'accuracy': score,
        'completeness': score,
        'clarity': score,
        'overall_score': score,
        'what_correct': "Unable to evaluate in detail",
        'what_missed': None,
        'what_wrong': None,
        'feedback': feedback,
        'training_content': [],
        'is_objection': question.get('is_objection', False)
    }
```

---

### 4. Database Methods for Objection Support

**File:** `database.py` (ADD THESE METHODS at end of Database class)

```python
    # ========================================================================
    # OBJECTION-HANDLING SPECIFIC OPERATIONS
    # ========================================================================
    
    def get_objection_performance(self, session_id: int) -> Dict:
        """Get objection-handling performance metrics for a session"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                AVG(CASE WHEN is_objection = 1 THEN overall_score ELSE NULL END) as objection_score,
                AVG(CASE WHEN is_objection = 1 THEN tone_score ELSE NULL END) as avg_tone,
                AVG(CASE WHEN is_objection = 1 THEN technique_score ELSE NULL END) as avg_technique,
                COUNT(CASE WHEN is_objection = 1 THEN 1 ELSE NULL END) as objection_count
            FROM answer_evaluations e
            JOIN question_bank q ON e.question_id = q.id
            WHERE e.session_id = ?
        ''', (session_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return {
            'objection_score': result['objection_score'] if result['objection_score'] else 0.0,
            'avg_tone': result['avg_tone'] if result['avg_tone'] else 0.0,
            'avg_technique': result['avg_technique'] if result['avg_technique'] else 0.0,
            'objection_count': result['objection_count']
        }
    
    def update_session_objection_score(self, session_id: int, objection_score: float):
        """Update session with objection-handling score"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE sessions 
            SET objection_score = ? 
            WHERE id = ?
        ''', (objection_score, session_id))
        
        conn.commit()
        conn.close()
```

---

## 🧪 TESTING REQUIREMENTS

### Unit Tests

Create `tests/test_objection_handling.py`:

```python
import pytest
from question_generator import generate_objection_scenarios, generate_questions_from_content
from answer_evaluator import evaluate_objection_handling

def test_objection_scenario_generation():
    """Test objection scenario generation at different levels"""
    
    # Basic level
    basic_scenarios = generate_objection_scenarios('basic')
    assert len(basic_scenarios) >= 2
    assert all(s['is_objection'] for s in basic_scenarios)
    assert all('forbidden_mistakes' in s for s in basic_scenarios)
    
    # Expert level
    expert_scenarios = generate_objection_scenarios('expert')
    assert len(expert_scenarios) >= 2
    assert len(expert_scenarios) >= len(basic_scenarios)  # More scenarios for expert


def test_objection_detection():
    """Test that Sales Objections category triggers special handling"""
    
    sample_content = "This is training content about handling objections."
    
    questions = generate_questions_from_content(
        content=sample_content,
        category="Sales Objections",
        difficulty="basic",
        num_questions=5
    )
    
    # Should include objection scenarios
    objection_questions = [q for q in questions if q.get('is_objection')]
    assert len(objection_questions) >= 2


def test_forbidden_mistake_detection():
    """Test that evaluator detects forbidden mistakes"""
    
    question = {
        'question_text': 'Customer says "I want it to last longer"',
        'expected_answer': 'Explain thin vs thick tradeoff',
        'key_points': ['thin vs thick', 'customer choice'],
        'forbidden_mistakes': ['apologizing', 'arguing'],
        'is_objection': True
    }
    
    # Answer with forbidden mistake (apologizing)
    bad_answer = "I'm sorry sir, but we can't do that. Our systems don't last long."
    
    evaluation = evaluate_objection_handling(
        question=question,
        user_answer=bad_answer,
        category="Sales Objections"
    )
    
    # Should have lower score due to apologizing
    assert evaluation['overall_score'] < 7.0
    assert 'forbidden_mistakes_made' in evaluation


def test_prescribed_language_bonus():
    """Test that using exact prescribed language gets bonus"""
    
    question = {
        'question_text': 'Handle longevity objection',
        'expected_answer': 'I understand, sir. A natural-looking system has to be thin. Thin things don\'t last long.',
        'key_points': ['thin vs thick', 'choice'],
        'forbidden_mistakes': [],
        'is_objection': True
    }
    
    # Answer using exact prescribed language
    perfect_answer = "I understand, sir. A natural-looking system has to be thin. Thin things don't last long. So it's a choice between natural look or long life."
    
    evaluation = evaluate_objection_handling(
        question=question,
        user_answer=perfect_answer,
        category="Sales Objections"
    )
    
    # Should have high score
    assert evaluation['overall_score'] >= 8.0
```

### Integration Test for Complete Objection Flow

Create `tests/test_objection_flow.py`:

```python
def test_complete_objection_training_session(client, db):
    """Test full training session with objections"""
    
    # 1. Login
    client.post('/api/auth/login', json={
        'username': 'testuser',
        'password': 'password'
    })
    
    # 2. Start session with Sales Objections category
    resp = client.post('/api/training/start', json={
        'category': 'Sales Objections',
        'difficulty': 'basic',
        'duration_minutes': 10
    })
    assert resp.status_code == 200
    session_id = resp.json['session_id']
    
    # 3. Prepare questions (should include objection scenarios)
    resp = client.post('/api/training/prepare', json={
        'session_id': session_id,
        'category': 'Sales Objections',
        'difficulty': 'basic'
    })
    assert resp.status_code == 200
    assert resp.json['questions_generated'] >= 5
    
    # 4. Get first question
    resp = client.post('/api/training/next-question', json={
        'session_id': session_id
    })
    assert resp.status_code == 200
    question = resp.json['question']
    question_id = question['id']
    
    # 5. Answer with good objection handling
    good_answer = "I understand sir. A natural system has to be thin, and thin things don't last as long. So you need to choose between natural look or long life. Which is more important to you?"
    
    resp = client.post('/api/training/evaluate-answer', json={
        'session_id': session_id,
        'question_id': question_id,
        'user_answer': good_answer
    })
    assert resp.status_code == 200
    eval = resp.json['evaluation']
    assert eval['score'] >= 7.0  # Good score for good answer
    
    # 6. Answer with forbidden mistake (apologizing)
    resp = client.post('/api/training/next-question', json={'session_id': session_id})
    if resp.json['has_more']:
        question_id = resp.json['question']['id']
        
        bad_answer = "I'm sorry sir, but that's just how it is. We can't change it."
        
        resp = client.post('/api/training/evaluate-answer', json={
            'session_id': session_id,
            'question_id': question_id,
            'user_answer': bad_answer
        })
        assert resp.status_code == 200
        eval = resp.json['evaluation']
        assert eval['score'] < 6.0  # Low score for apologizing
    
    # 7. End session and get report
    client.post('/api/training/end', json={'session_id': session_id})
    
    resp = client.get(f'/api/training/report/{session_id}')
    assert resp.status_code == 200
    report = resp.json
    
    # Report should include objection-specific metrics
    assert 'objection_score' in report or 'Objection' in report.get('report_html', '')
```

### Manual Testing Checklist for Objections

- [ ] Can upload Master Objection Script
- [ ] Sales Objections category detected automatically
- [ ] Objection scenarios generated correctly
- [ ] Questions include objection scenarios
- [ ] Evaluation stricter for objections
- [ ] Forbidden mistakes detected
- [ ] Penalty applied for apologizing
- [ ] Penalty applied for arguing
- [ ] Bonus given for exact language
- [ ] Report shows objection performance separately
- [ ] Report highlights which objections handled well
- [ ] Report recommends script sections to review
- [ ] Tone score calculated correctly
- [ ] Technique score calculated correctly
- [ ] All difficulty levels work for objections
- [ ] Expert level has harder objection scenarios

---

## 📦 DEPLOYMENT CHECKLIST

### Pre-Deployment

#### Content Preparation
- [ ] Master Objection Script created
- [ ] Script formatted properly
- [ ] Script saved as .txt file
- [ ] All objection scenarios included
- [ ] Forbidden mistakes listed
- [ ] Key points identified

#### Code Changes
- [ ] Database migration tested
- [ ] `question_generator.py` completed
- [ ] `answer_evaluator.py` completed
- [ ] Backend endpoints updated
- [ ] Frontend updated for objections
- [ ] All unit tests passing
- [ ] Integration tests passing

#### Content Upload
- [ ] Master Objection Script uploaded
- [ ] Verified in Pinecone
- [ ] Can retrieve objection content
- [ ] Test question generation with objections
- [ ] Test evaluation with objection answers

### Deployment Steps

```bash
# 1. Backup database
cp data/sales_trainer.db data/sales_trainer_backup_$(date +%Y%m%d).db

# 2. Upload Master Objection Script
# Via admin interface:
# - Category: Sales Objections
# - Video Name: Master Objection Handling Script
# - File: Sales_Objections_Master_Script.txt

# 3. Run migration
python add_question_system.py

# 4. Test objection question generation
python -c "
from question_generator import generate_objection_scenarios
scenarios = generate_objection_scenarios('basic')
print(f'Generated {len(scenarios)} objection scenarios')
for s in scenarios:
    print(f\"  - {s['question'][:60]}...\")
"

# 5. Test complete flow with Sales Objections
# Start session with category "Sales Objections"
# Verify objection scenarios appear
# Answer and verify stricter evaluation

# 6. Deploy to production
# Follow your normal deployment process

# 7. Verify objection handling works
# Test with 1-2 real users
```

### Post-Deployment

- [ ] Verify objection scenarios generated
- [ ] Test complete objection session
- [ ] Check reports show objection scores
- [ ] Verify penalties work
- [ ] Verify bonuses work
- [ ] Monitor logs for errors
- [ ] Get feedback from sales manager
- [ ] Adjust rubric if needed

---

## 📊 SUCCESS METRICS

### Quantitative Metrics

**Week 1 Targets:**
- Question generation time: < 10 seconds
- Answer evaluation time: < 3 seconds
- Report generation time: < 5 seconds
- System uptime: > 99%
- Test coverage: > 80%
- **🆕 Objection evaluation accuracy: > 90% (vs sales manager)**

**Week 2 Targets:**
- User engagement: +50% (time in session)
- Completion rate: > 90%
- Evaluation accuracy: > 85% (compared to human trainer)
- User satisfaction: > 4/5 stars
- **🆕 Objection handling scores improve over time**
- **🆕 Sales conversion rates increase**

### Qualitative Metrics

**User Feedback Targets:**
- "Questions feel relevant" - > 80% agree
- "Feedback is helpful" - > 80% agree
- "Report is actionable" - > 80% agree
- "System is engaging" - > 70% agree
- **🆕 "Objection training is realistic" - > 85% agree**
- **🆕 "Feel more confident handling objections" - > 80% agree**

### Business Impact Metrics

**Sales Performance:**
- **🆕 Objection conversion rate improvement:** Target +15%
- **🆕 Average deal size increase:** Target +10%
- **🆕 Sales consultant confidence:** Target >8/10
- **🆕 New hire ramp-up time:** Target -30%

---

## 🎯 FINAL SUMMARY

### What's New in V3.1

1. **Master Objection Script Integration**
   - Complete company methodology documented
   - Uploaded as training content
   - Referenced in all evaluations

2. **Objection-Specific Question Generation**
   - 6+ scenario-based questions
   - Mix of prescribed responses
   - Covers all common objections

3. **Stricter Objection Evaluation**
   - Tone and technique scoring
   - Forbidden mistake detection
   - Prescribed language bonus

4. **Enhanced Reporting**
   - Separate objection-handling score
   - Highlights strengths/weaknesses
   - Script section references

### Total Effort Updated

**Original Estimate:** 27-36 hours  
**With Objection Integration:** 30-42 hours  
**Additional Time:** 3-6 hours

**Breakdown:**
- Content preparation: 1 hour
- Question generation updates: 2 hours
- Evaluation updates: 2 hours
- Testing: 1 hour

### Priority

This integration is **P0 - Critical** because:
- Tests company-specific methodology
- Ensures consistent customer experience
- Directly impacts sales conversion rates
- Reduces manager training time

---

## ✅ APPROVAL & SIGN-OFF

### Requirements Confirmed

✅ AI acts as customer (natural questions)  
✅ System evaluates like trainer (validates answers)  
✅ Wrong answers: Skip and move on  
✅ Evaluation: Allow paraphrasing  
✅ Feedback: Real-time after each answer  
✅ Difficulty: Exactly as specified  
✅ Report: Shows Q&A comparison with evidence  
✅ **🆕 Objection handling: Prescribed methodology tested**  
✅ **🆕 Evaluation: Stricter for sales objections**  
✅ **🆕 Report: Highlights objection performance**

### Manager Approval

**Manager:** ___________________  
**Date:** ___________________  
**Signature:** ___________________

### Developer Acknowledgment

**Developer:** ___________________  
**Date:** ___________________  
**I have read and understood:** ___________________

---

**Document Version:** 3.1  
**Last Updated:** December 18, 2025  
**Status:** Approved - Ready for Development with Objection Integration  
**Next Review:** December 25, 2025

---

**Remember:**
- Objection integration adds 3-6 hours
- Follow day-by-day plan
- Upload objection script first
- Test objection scenarios thoroughly
- Get sales manager feedback early

**Good luck! This will be a game-changer for your sales training! 💪🚀**
