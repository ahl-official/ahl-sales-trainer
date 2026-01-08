# System Overview & Technical Documentation

## 1. System Overview
The **AHL Training LMS (AI-Powered)** is a comprehensive Learning Management System designed to deliver personalized, adaptive learning experiences. It leverages Artificial Intelligence to generate dynamic tests, simulate realistic customer service calls, and provide real-time feedback. The system is built on a monolithic Node.js/Express architecture with a SQLite database, ensuring portability and ease of deployment.

### Key Capabilities
*   **Adaptive Learning**: Dynamically adjusts test difficulty and content based on student performance and learning style.
*   **AI Mock Calls**: Simulates voice-based customer service scenarios with AI analysis of sentiment, tone, and resolution skills.
*   **Intelligent Content**: Generates flashcards, notes, mind maps, and visual aids automatically from video transcripts.
*   **Role-Based Access**: Granular permissions for Admins, Trainers, and Students.
*   **Media Processing**: Integrated text-to-speech (TTS), speech-to-text (STT), and video streaming via Gumlet.

---

## 2. Technical Architecture

### Stack
*   **Runtime**: Node.js
*   **Framework**: Express.js
*   **Database**: SQLite (`lms_database.db`)
*   **Authentication**: Session-based + JWT (for specific API flows)
*   **Security**: Helmet (CSP), Rate Limiting, bcryptjs
*   **AI Providers**: OpenAI, OpenRouter (DeepSeek, Google Gemini)
*   **Media**: Fluent-FFmpeg (Audio processing), Gumlet (Video hosting)

### Design Patterns
*   **Monolithic Controller**: `server.js` acts as the central entry point, initializing database connections, middleware, and mounting routes.
*   **Service Layer**: Business logic is encapsulated in dedicated service classes (e.g., `AdaptiveLearningService`, `MockCallService`) to keep controllers thin.
*   **Singleton/Dependency Injection**: Services are instantiated once and injected or reused across routes.

---

## 3. Directory Structure

```
/
├── server.js                   # Application entry point, DB init, Middleware config
├── package.json                # Dependencies and scripts
├── lms_database.db             # SQLite Database file
├── public/                     # Static frontend assets
│   ├── admin/                  # Admin dashboard & management interfaces
│   ├── student/                # Student learning interfaces
│   ├── trainer/                # Trainer dashboard & grading interfaces
│   ├── css/                    # Global stylesheets
│   ├── js/                     # Shared JavaScript utilities
│   └── uploads/                # Publicly accessible uploads (if configured)
├── routes/                     # API Route Definitions
│   ├── ai-test-routes.js       # Endpoints for adaptive testing
│   ├── mock-call-routes.js     # Endpoints for mock call simulation
│   ├── audio-routes.js         # Endpoints for audio upload/TTS/STT
│   └── learning-tools-routes.js # Endpoints for flashcards, notes, mind maps
├── middleware/                 # Custom Express Middleware
│   └── auth.js                 # Authentication & Role verification
├── services/ (implicit root)   # Business Logic Classes
│   ├── ai_service.js           # Wrapper for OpenAI/OpenRouter APIs
│   ├── adaptive_learning_service.js # Logic for adaptive tests & profiles
│   ├── mock_call_service.js    # Logic for call simulation & analysis
│   ├── audio_service.js        # Logic for ffmpeg, TTS, STT
│   └── gumlet_service.js       # Logic for video transcripts
├── uploads/                    # User generated content storage
│   ├── audio/                  # Uploaded audio files
│   ├── tts/                    # Generated speech files
│   ├── mock_calls/             # Recorded mock call sessions
│   └── call_analysis/          # JSON analysis reports
└── docs/                       # System documentation
```

---

## 4. Database Schema

The SQLite database is structured into three logical domains: **Core**, **AI/Adaptive**, and **Mock Call**.

### Core Domain
*   **`users`**: Stores user credentials and roles (`admin`, `trainer`, `student`).
*   **`roles`**: System role definitions.
*   **`courses`**: Course metadata.
*   **`course_levels`** & **`course_chapters`**: Hierarchical course structure.
*   **`videos`**: Video content metadata, linked to Gumlet assets.
*   **`progress`**: Tracks video completion status (`not_started`, `watching`, `completed`).
*   **`activities`** & **`submissions`**: Manual assignments and student submissions.
*   **`trainer_course_assignments`**: Maps trainers to specific courses.

### AI & Adaptive Learning Domain
*   **`system_settings`**: Key-value store for API keys (`openai_api_key`, `openrouter_api_key`).
*   **`video_transcripts`**: Stores raw text transcripts linked to `videos`.
*   **`adaptive_learning_profiles`**:
    *   `user_id`: FK to users.
    *   `learning_style`: 'visual', 'auditory', 'textual', 'kinesthetic'.
    *   `performance_trend`: 'improving', 'stable', 'declining'.
    *   `question_type_preferences`: JSON (weights for MCQ, Typing, Audio, Scenario).
*   **`learning_path_progress`**:
    *   Tracks mastery level per video/topic.
    *   `is_mastered`: Boolean flag.
    *   `attempts_count`: Number of test attempts.
*   **`test_sessions`**:
    *   Active test instances.
    *   `status`: 'in_progress', 'completed'.
    *   `question_sequence`: JSON array of generated questions.
*   **`test_results`**:
    *   Completed test outcomes.
    *   `score`, `mastery_level`, `time_taken`.
    *   `feedback`: AI-generated feedback.
*   **`student_weak_areas`**:
    *   Specific topics where the student struggles, used to bias future question generation.
*   **`flashcards`**: AI-generated study cards (`front`, `back`).
*   **`student_notes`**: AI-generated or user-edited notes.
*   **`visual_aids`**: Mermaid.js code for generated diagrams.
*   **`mind_maps`**: JSON structure for mind map visualization.

### Mock Call Domain
*   **`mock_call_sessions`**:
    *   `student_id`: FK to users.
    *   `scenario_type`: 'customer_complaint', 'sales_pitch', etc.
    *   `recording_path`: Path to WAV file.
    *   `overall_score`: AI-calculated score (0-100).
*   **`mock_call_analysis`**:
    *   Detailed breakdown (`sentiment`, `transcription`, `feedback`).
*   **`mock_call_criteria_scores`**:
    *   Granular scoring per scenario criterion (e.g., "Empathy", "Closing").

---

## 5. Services & Business Logic

### `AIService` (`ai_service.js`)
The central hub for all AI interactions.
*   **Providers**: Supports OpenAI (GPT-3.5/4) and OpenRouter (DeepSeek, Gemini).
*   **Key Methods**:
    *   `initialize(openaiKey, openrouterKey)`: Sets up API clients.
    *   `getSafeProviderAndModel()`: Intelligent fallback mechanism. Prefers OpenAI, falls back to OpenRouter if configured.
    *   `generateContent(prompt)`: Generic text generation.
    *   `generateTestQuestions(videoId, transcript)`: Generates JSON-formatted multiple-choice questions.
    *   `generateActivity(videoId, transcript)`: Creates practical activities based on video content.
    *   `extractAudioFromGumletUrl(url)`: Helper to extract audio for transcription if direct download fails.

### `AdaptiveLearningService` (`adaptive_learning_service.js`)
Manages the personalized testing lifecycle.
*   **Key Methods**:
    *   `initializeUserProfile(userId)`: Creates a default learning profile (balanced preferences).
    *   `generateAdaptiveTest(userId, videoId)`:
        1.  Checks if transcript exists.
        2.  Analyzes user's `adaptive_learning_profile`.
        3.  Identifies weak areas from `student_weak_areas`.
        4.  Constructs a prompt for the AI to generate questions tailored to difficulty and learning style.
    *   `scoreAdaptiveTest(session, answers)`:
        1.  Compares user answers against correct answers.
        2.  Calculates score and mastery level (threshold: 70%).
        3.  Updates `learning_path_progress`.
        4.  Updates `adaptive_learning_profile` based on performance (e.g., increase difficulty if high score).

### `MockCallService` (`mock_call_service.js`)
Simulates and analyzes customer service calls.
*   **Scenarios**: Hardcoded scenarios (e.g., 'Customer Complaint', 'Sales Pitch') with specific evaluation criteria.
*   **Key Methods**:
    *   `startMockCallSession(studentId, scenarioType)`: Creates a new session entry.
    *   `completeMockCallSession(sessionId, recordingData)`: Saves the audio file and triggers background analysis.
    *   `analyzeCallRecording(sessionId)`:
        1.  **Transcribe**: Converts audio to text.
        2.  **Sentiment**: Analyzes tone (professional, empathetic, etc.).
        3.  **Criteria**: Evaluates against scenario-specific criteria.
        4.  **Feedback**: Generates strengths and improvements.

### `AudioService` (`audio_service.js`)
Handles media file operations.
*   **Key Methods**:
    *   `convertAudioFormat(input, output)`: Uses `fluent-ffmpeg` to convert uploads to standard WAV format (16kHz mono).
    *   `generateSpeech(text)`: Uses local Coqui TTS (via command line) to generate audio prompts.
    *   `transcribeAudio(path)`: Uses OpenAI Whisper for high-accuracy Speech-to-Text.
    *   `analyzeAudioQuality(path)`: Checks bitrate, sample rate, and duration.

### `GumletService` (`gumlet_service.js`)
Bridge to Gumlet video hosting.
*   **Key Methods**:
    *   `getTranscript(videoId, gumletUrl)`: Attempts to fetch subtitles/transcripts from Gumlet.
    *   `vttToPlainText(vtt)`: Parses WebVTT subtitle format into clean text for AI processing.
    *   *Note*: Handles the limitation where Gumlet doesn't provide direct API access to subtitle files by guiding users to the dashboard.

---

## 6. Detailed API Reference

### Adaptive Testing (`/api/ai-test`)

| Method | Endpoint | Description | Request Body | Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/generate` | Generate a new test | `{ videoId, difficulty, questionCount }` | `{ success, testId, message }` |
| `POST` | `/submit` | Submit test answers | `{ sessionId, answers: [{ questionId, answer }] }` | `{ score, masteryAchieved, feedback, nextAction }` |
| `GET` | `/history/:videoId` | Get past results | - | `{ history: [results] }` |
| `GET` | `/weak-areas/:videoId` | Get weak topics | - | `{ weakAreas: [topics] }` |
| `GET` | `/leaderboard` | Get rankings | - | `{ leaderboard: [{ user, score }] }` |

### Mock Calls (`/api/mock-call`)

| Method | Endpoint | Description | Request Body | Response |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/scenarios` | List scenarios | - | `[{ id, title, difficulty, criteria }]` |
| `POST` | `/start` | Start session | `{ scenarioType, videoId }` | `{ success, session: { id, scenario } }` |
| `POST` | `/complete/:sessionId` | Upload recording | `Multipart Form: recording (file)` | `{ success, analysisStarted: true }` |
| `GET` | `/results/:sessionId` | Get analysis | - | `{ score, transcription, sentiment, feedback }` |
| `GET` | `/recording/:sessionId` | Stream audio | - | Binary Audio Stream |

### Audio (`/api/audio`)

| Method | Endpoint | Description | Request Body | Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/upload` | Upload audio | `Multipart Form: audio (file)` | `{ success, url, duration }` |
| `POST` | `/tts/generate` | Generate speech | `{ text, options: { speed, pitch } }` | `{ success, url, duration }` |
| `POST` | `/transcribe` | Transcribe file | `Multipart Form: audio (file)` | `{ success, transcription, confidence }` |
| `GET` | `/tts/:filename` | Stream TTS file | - | Binary Audio Stream |

### Learning Tools (`/api/tools`)

| Method | Endpoint | Description | Request Body | Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/flashcards/generate` | Create flashcards | `{ videoId }` | `{ success, flashcards: [{ front, back }] }` |
| `GET` | `/flashcards/:videoId` | Get flashcards | - | `{ flashcards: [] }` |
| `POST` | `/notes/generate` | AI-summarize | `{ videoId }` | `{ success, notes: { summary, keyPoints } }` |
| `POST` | `/mindmap/generate` | Generate Mind Map | `{ videoId }` | `{ success, mindmap: { root: {} } }` |
| `POST` | `/visuals/generate` | Generate Diagram | `{ videoId, type }` | `{ success, mermaidCode }` |

---

## 7. Frontend Structure (`public/`)

The frontend follows a multi-role dashboard structure:

*   **`admin/`**:
    *   `dashboard.html`: System overview.
    *   `users.html`: User management.
    *   `courses.html`: Course & video management.
    *   `ai-config.html`: Configure API keys (OpenAI/OpenRouter).
*   **`student/`**:
    *   `dashboard.html`: Learning progress.
    *   `course-view.html`: Video player & lesson navigation.
    *   `adaptive-test.html`: Interface for taking AI tests.
    *   `mock-call.html`: Interface for recording mock calls.
    *   `tools.html`: Access to flashcards, notes, and mind maps.
*   **`trainer/`**:
    *   `dashboard.html`: Student progress overview.
    *   `grading.html`: Manual grading interface.

---

## 8. Configuration & Environment

The system uses `process.env` and database-stored settings.

### Environment Variables (`.env` or System)
*   `PORT`: Server port (default: 3000)
*   `ENABLE_TTS`: Enable/disable local TTS generation (`true`/`false`)
*   `OPENAI_API_KEY`: (Optional) Fallback if not in DB.

### Database Settings (`system_settings` table)
*   `openai_api_key`: Primary OpenAI key.
*   `openrouter_api_key`: Primary OpenRouter key.
*   `default_ai_provider`: Preferred provider (`openai` or `openrouter`).
*   `default_openai_model`: e.g., `gpt-4`.
*   `default_openrouter_model`: e.g., `deepseek/deepseek-chat-v3.1:free`.

---

## 9. Key Workflows

### Adaptive Test Generation Flow
1.  **Trigger**: User finishes video or requests test.
2.  **Check**: `AdaptiveLearningService.shouldTriggerAdaptiveTest` verifies mastery status.
3.  **Generate**: `AdaptiveLearningService.generateAdaptiveTest` calls `AIService` with context (transcript + user weak areas).
4.  **Serve**: Frontend receives JSON questions.
5.  **Submit**: User submits answers -> `scoreAdaptiveTest` calculates result.
6.  **Adapt**: If score > 70%, mark mastered; else, record weak areas for next time.

### Mock Call Simulation Flow
1.  **Select**: Student chooses "Customer Complaint" scenario.
2.  **Record**: Browser records audio -> Uploads to `/api/mock-call/complete/:id`.
3.  **Process**: Server saves WAV -> `MockCallService` triggers async analysis.
4.  **Analyze**: AI transcribes text -> Analyzes sentiment -> Scores against criteria (e.g., "Empathy").
5.  **Feedback**: Student receives detailed report with "Strengths" and "Improvements".
