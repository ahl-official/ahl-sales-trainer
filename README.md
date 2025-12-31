# 🎓 AHL SALES TRAINER V2 - COMPLETE SYSTEM

## ✅ SYSTEM COMPLETE - ALL FILES CREATED!

### 📂 FOLDER STRUCTURE
```
sales-trainer-v2/
├── backend/
│   ├── app.py                  ✅ Main Flask server (all APIs)
│   ├── database.py             ✅ SQLite database layer
│   └── requirements.txt        ✅ Python dependencies
│
├── frontend/
│   ├── login.html              ✅ Login page (admin & candidates)
│   ├── admin-upload.html       ✅ Upload content & create users
│   ├── admin-dashboard.html    ✅ View all candidate results
│   └── trainer.html            ✅ Category-based training interface
│
├── data/
│   └── sales_trainer.db        (auto-created on first run)
│
├── .env.example                ✅ Template for API keys
└── README.md                   ✅ This file
```

---

## ⚡ QUICK START (5 MINUTES)

### Step 0: Generate SECRET_KEY
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```
Copy the 64-character output and set `SECRET_KEY` in your `.env`.

### Step 1: Create .env file
Copy `.env.example` to `.env` and add your API keys:

```bash
cp .env.example .env
```

Then edit `.env` with your actual keys:
```env
OPENROUTER_API_KEY=sk-or-v1-YOUR_ACTUAL_KEY
OPENAI_API_KEY=sk-YOUR_ACTUAL_KEY
PINECONE_API_KEY=pcsk_YOUR_ACTUAL_KEY
PINECONE_INDEX_HOST=https://your-index.svc.region.pinecone.io
SECRET_KEY=generate_random_string_here
PORT=5050
```

### Step 2: Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Step 3: Start Backend Server
```bash
# from the project root
PORT=5050 python3 backend/app.py
```

**Expected Output:**
```
✅ Database initialized successfully
✅ Default admin created (admin/admin123)
🚀 AHL Sales Trainer Backend Running on http://localhost:5050
```

### Step 4: Start Frontend Server
```bash
# from the project root
python3 -m http.server 8000 -d frontend
```
Open `http://localhost:8000/login.html` in your browser (Chrome or Edge recommended)

**Default Login:** `admin / admin123`

---

## 📖 COMPLETE USER GUIDE

### 👨‍💼 FOR ADMIN (You)

#### 1️⃣ First Login
- Open `frontend/login.html`
- Login: `admin / admin123`
- You'll see the Upload page

#### 2️⃣ Create Candidate Accounts
On the Upload page, find "Create Candidate Account" section:
- **Username**: e.g., `rahul.kumar`
- **Password**: e.g., `Test123`
- **Full Name**: e.g., `Rahul Kumar`
- Click "Create Candidate"
- Share credentials with candidate

#### 3️⃣ Upload Training Content
For each video transcript:
- **Category**: Select from 12 categories
- **Video Name**: e.g., "Video 1 - Sales Script Mastery"
- **File**: Choose .txt transcript
- Click "Upload to Pinecone"
- Wait 30-60 seconds for processing

**Repeat for all 37 videos across 12 categories**

#### 4️⃣ View Dashboard
- Click "Dashboard" button
- See all candidate performance
- Click on any category to view sessions
- Click on any session to see detailed report

---

### 👨‍🎓 FOR CANDIDATES (Your Team)

#### 1️⃣ Login
- Open `frontend/login.html`
- Use credentials provided by admin
- You'll see available training categories

#### 2️⃣ Select Training Category
- Choose from available categories (only uploaded ones show)
- Each card shows:
  - Number of videos in that category
  - Your previous scores (if any)

#### 3️⃣ Configure Training
- **Difficulty**: New Joining → Basic → Experienced → Expert
- **Duration**: 5-20 minutes
- Click "Start Training Session"
- **Allow microphone access** when prompted

#### 4️⃣ Complete Training
- AI asks questions from selected category ONLY
- Speak your answers naturally (don't worry about "um"s or "uh"s)
- The system focuses on **meaning**, not perfect grammar
- Click "I'm Done Speaking" when finished talking
- Session ends automatically or click "End Session"

#### 5️⃣ View Report
- Detailed performance analysis appears
- Scores for knowledge, proficiency, methodology
- Actionable recommendations
- Click "Start New Session" to practice again

---

## 🎯 YOUR 12 CATEGORIES (Upload Order)

| # | Category | Videos | Status |
|---|----------|--------|--------|
| 1 | Pre Consultation | 1 video | ⬜ Upload |
| 2 | Consultation Series | 15 videos | ⬜ Upload |
| 3 | Sales Objections | 6 videos | ⬜ Upload |
| 4 | After Fixing Objection | 3 videos | ⬜ Upload |
| 5 | Full Wig Consultation | 2 videos | ⬜ Upload |
| 6 | Hairline Consultation | 2 videos | ⬜ Upload |
| 7 | Types of Patches | 1 video | ⬜ Upload |
| 8 | Upselling / Cross Selling | 3 videos | ⬜ Upload |
| 9 | Retail Sales | 1 video | ⬜ Upload |
| 10 | SMP Sales | 2 videos | ⬜ Upload |
| 11 | Sales Follow up | 1 video | ⬜ Upload |
| 12 | General Sales | 1 video | ⬜ Upload |

**Total: 37 videos across 12 categories**

---

## 🔐 SECURITY FEATURES

✅ **API keys stored server-side only** - Never exposed to browser  
✅ **Session-based authentication** - Secure login system  
✅ **Password hashing** - SHA256 encryption  
✅ **Role-based access** - Admin vs Candidate permissions  
✅ **Protected endpoints** - Authentication required  
✅ **Dynamic Rate Limiting** - Protects against abuse (e.g., 120 uploads/hr for admins, 5 logins/min)  

---

## 📊 SYSTEM FEATURES

### ✨ What This System Does

**For Admins:**
- ✅ Upload transcript files to Pinecone by category and video
- ✅ Create/manage candidate accounts and roles
- ✅ View all candidate performance with filters
- ✅ Open detailed HTML reports per session with scores
- ✅ Track progress over time across categories

**For Candidates:**
- ✅ Select specific category to train on
- ✅ Voice-based conversation with AI
- ✅ AI asks questions ONLY from the selected category (strict question-only)
- ✅ Human-like phrasing with one question per turn
- ✅ **Forgiving AI Evaluation**: Ignores filler words ("um", "uh"), accepts paraphrasing, and focuses on core meaning
- ✅ **Supportive Feedback**: Constructive coaching that praises correct concepts even if grammar is imperfect
- ✅ Automatic session recording and safe session end
- ✅ Detailed, styled performance reports with numeric scores
- ✅ Track improvement over multiple sessions

**Technical:**
- ✅ Retrieval-Augmented Generation via Pinecone namespaces per category/video
- ✅ SQLite database for users, sessions, messages, and reports
- ✅ Real-time voice recognition and speech synthesis in browser
- ✅ Report generator outputs raw HTML with meta tags (overall_score, category)
- ✅ Backend reads `PORT` from environment and enables CORS with credentials

---

## 🐛 TROUBLESHOOTING

### ❌ "Server not running"
**Fix:**
```bash
cd backend
python app.py
```
Make sure you see the success messages.

### ❌ "Invalid credentials"
**Fix:**
Default admin: `admin / admin123`  
Change password after first login.

### ❌ "Upload failed"
**Fix:**
1. Check `.env` has correct Pinecone API key
2. Verify Pinecone index exists
3. Make sure file is `.txt` format
4. Check backend console for detailed error

### ❌ "Network error" / "CORS error"
**Fix:**
1. Backend must run on `http://localhost:5000`
   - You can override with `PORT=5050` (recommended)
2. Ensure the frontend is served from `http://localhost:8000`
3. Run: `PORT=5050 python3 backend/app.py`

### ❌ "Microphone not working"
**Fix:**
1. Use Chrome or Edge browser
2. Allow microphone access when prompted
3. Check browser settings → Permissions → Microphone
4. Make sure no other app is using microphone

### ❌ "No categories showing"
**Fix:**
1. Upload at least one video transcript first
2. Refresh the page
3. Check "Upload Statistics" section on admin page

---

## 📞 GETTING HELP

**Check Logs:**
- Backend: Look at terminal running `python app.py`
- Frontend: Press F12 → Console tab in browser

**Common Issues:**
- All API keys must be valid
- Pinecone index must exist
- Port 5000 must be free
- Use Chrome or Edge browser

---

## 🚀 SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────────┐
│         FRONTEND (Browser)                  │
│  • login.html - Authentication              │
│  • admin-upload.html - Content management   │
│  • admin-dashboard.html - View results      │
│  • trainer.html - Training interface        │
│  • Served via Python HTTP server on port 8000
└─────────────────────────────────────────────┘
                    ↓ HTTP/REST API
┌─────────────────────────────────────────────┐
│      BACKEND (Flask Server - PORT env)       │
│      Default 5000, using 5050 in this setup  │
│  • app.py - Main server & API routes        │
│  • database.py - SQLite operations          │
│  • Authentication & Session management      │
│  • Proxy to OpenRouter/OpenAI/Pinecone      │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│           DATA LAYER                        │
│  • SQLite (sales_trainer.db)               │
│    - users, sessions, messages, reports     │
│  • Pinecone (Vector Database)              │
│    - Embeddings by category/video          │
└─────────────────────────────────────────────┘
```

---

## 🎉 YOU'RE READY!

### Next Steps:
1. ✅ Run backend: `python backend/app.py`
2. ✅ Open `frontend/login.html`
3. ✅ Login as admin
4. ✅ Create 2-3 candidate accounts
5. ✅ Upload 1-2 test transcripts
6. ✅ Test with candidates
7. ✅ Upload remaining 35 transcripts
8. ✅ Train your team!

**System is 100% COMPLETE and READY FOR PRODUCTION USE!** 🚀
