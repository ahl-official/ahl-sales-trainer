# AHL Sales Trainer - Starter Guide

Welcome to the AHL Sales Trainer Application! This system is designed to help sales candidates practice their consultation skills through an AI-powered roleplay simulation.

## 🚀 Quick Start

### 1. Running the Application
The application runs on a local server.
1.  Open your terminal in the project directory.
2.  Run the backend server:
    ```bash
    python backend/app.py
    ```
3.  Open your web browser and navigate to:
    **[http://localhost:5050](http://localhost:5050)**

---

## 👥 User Roles & Credentials

### **Admin Access**
- **URL**: `http://localhost:5050/login.html`
- **Username**: `admin`
- **Password**: `admin123`
- **Capabilities**:
    - View all candidate sessions and scores.
    - Delete sessions (single or bulk).
    - Manage candidates (delete users).
    - Sync content with the AI database (Pinecone).

### **Candidate (Student) Access**
- **URL**: `http://localhost:5050/login.html`
- **Registration**: New users can click "Register" to create an account.
- **Capabilities**:
    - Start new training sessions.
    - View personal history and past reports.
    - Practice specific sales categories.

---

## 🎓 Training Session Guide

1.  **Dashboard**: After logging in, you will see your dashboard. Click **"Start New Session"**.
2.  **Configuration**:
    - Select a **Category** (e.g., Pre Consultation, Sales Objections).
    - Select a **Difficulty** (New Joining, Basic, Experienced, Expert).
    - Select **Duration** (5, 10, 15, 20, or 30 minutes).
3.  **The Session**:
    - A **3-second countdown** will start.
    - The AI will **automatically speak** the first question.
    - **Speak your answer** clearly into the microphone.
    - The system automatically detects when you stop speaking.
    - **Feedback**: The AI will evaluate your answer and provide spoken feedback before moving to the next question.
    - **Controls**: You can Pause/Resume the session if needed.
4.  **Completion**:
    - When the timer ends or you finish all questions, the session concludes.
    - A detailed **Performance Report** is generated with scores out of 10.

---

## 🛠 Admin Dashboard Features

### **Overview Stats**
- View total candidates, completed sessions, and average scores across the organization.

### **Candidate Management**
- **Search**: Find candidates by name or email.
- **View Reports**: Click on a candidate to expand their history and view detailed session reports.
- **Delete Candidate**: Remove a candidate and all their associated data.

### **Session Management**
- **Delete Session**: Remove individual practice sessions if needed.
- **Bulk Delete**: Select multiple sessions to delete them at once.

### **System Maintenance**
- **Sync Content**: If you've added new training videos or materials to the vector database, click **"Sync Content"** to update the local system references.

---

## ❓ Troubleshooting

**Q: The AI isn't hearing me.**
- A: Ensure your microphone permissions are allowed in the browser. Check if the "Listening..." indicator is active.

**Q: The flow feels choppy.**
- A: The system is designed to wait for your full answer. Ensure you speak clearly. If the AI interrupts, try to minimize background noise.

**Q: I get a "Database Locked" error.**
- A: This can happen if multiple operations are trying to write at the same time. Wait a few seconds and try again; the system has built-in retry logic.

**Q: Reports show 0.0/10 scores.**
- A: This usually means the answer was too short or irrelevant. Try to provide comprehensive answers based on the training material.
