# SkillForge AI — Enterprise-Grade Career Development Platform

SkillForge AI is an advanced, AI-driven platform designed to provide a comprehensive, end-to-end career growth experience. It combines high-speed AI modeling with robust proctoring and evaluation systems to prepare users for the modern job market.

---

## 🚀 Key Features

### 1. **AI Career Coach & Evaluation System**
- **Market Alignment Analysis**: Get a deep-dive analysis of how your current skills match your target role, including a **Match Percentage**, **Strong Skills**, and **Missing Critical Skills**.
- **Job Readiness Level**: Evaluates if you are *Beginner*, *Job-Ready*, or *Competitive* in the current market.
- **Intensive 30-Day Roadmaps**: Generates a week-by-week learning plan with curated free resources to bridge your skill gaps.
- **Adaptive Learning**: Identifies weak areas from previous performance and adjusts roadmap focus.

### 2. **Skill Verification & Anti-Cheat Challenge**
- **Adaptive Quizzes**: Generates 10 multiple-choice questions based on a topic and chosen difficulty (*Beginner*, *Moderate*, *Advanced*).
- **Real-World Scenarios**: Instead of generic questions, the system generates complex, industry-specific challenges to verify technical depth.
- **Oral Justification (Anti-Cheat)**: Provides 3–5 conceptual "Why" and "What-if" follow-up questions that cannot be answered by memorization alone.

### 3. **Proctor Mode (Enterprise Anti-Cheating)**
- **AI Webcam Monitoring**: Uses `face-api.js` for real-time face detection during high-stakes evaluations.
- **Mobile Phone Detection**: Integrated with **TensorFlow.js (COCO-SSD)** to detect if a candidate is using a mobile phone during the test.
- **Eye & Focus Tracking**: Monitors head orientation and gaze to ensure the user stays focused on the screen.
- **Violation Logging**: Automatically logs suspicious activity (looking away, face missing, mobile phone usage) to the backend `CheatLog`.

### 4. **Adaptive Learning & Mock Interviews**
- **Realistic Mock Interviews**: Conducts role-specific interview simulations with real-time feedback on your performance.
- **AI Feedback Engine**: Provides structured JSON feedback on content, confidence, and areas for improvement.
- **Progress Analytics**: Visualizes your learning journey and topic mastery using radar charts powered by `Chart.js`.

---

## 💼 B2B & Recruiter Solutions

SkillForge AI is built for both **B2C (Students)** and **B2B (Organizations)**. Companies can use the **Recruiter Dashboard** to:
- **Monitor Candidate Performance**: Access detailed reports on quiz scores and interview performance.
- **Verified Skill Scores**: See objective, AI-verified scores for technical and soft skills.
- **Cheat Probability Score**: Use our proprietary heuristic model to assess the integrity of candidate evaluations based on proctoring data and behavior logs.
- **Admin Access Control**: Dedicated `is_admin` role for recruiters to access private candidate analytics.

---

## 🛠️ Tech Stack

- **AI Engine**: **Groq API** (Llama-3.3-70b-versatile) for near-instant, high-intelligence processing.
- **Computer Vision**: 
  - **face-api.js** for client-side proctoring (webcam/face detection).
  - **TensorFlow.js + COCO-SSD** for real-time object/mobile phone detection.
- **Backend**: Python 3.10+ with **Flask** and **SQLAlchemy**.
- **Database**: **SQLite** (absolute pathing for consistency) for robust session and history management.
- **Frontend**: Responsive **HTML5 / CSS3 / JavaScript** with **Chart.js** integration.

---

## 📂 Project Structure

- `app.py`: Main API server, AI orchestration, and proctoring logs.
- `database.py`: Schema definitions for Users, Roadmaps, Interviews, and Quiz Results.
- `templates/`: Modern UI templates with integrated proctoring overlays.
- `check_db.py`: Helper script for direct database auditing.
- `migrate_db.py`: Database migration script for schema updates.
- `.env`: Secure configuration for API keys.

---

## ⚙️ Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Setup Environment**:
   Create a `.env` file and add:
   ```env
   GROQ_API_KEY=your_api_key_here
   FLASK_SECRET_KEY=your_secret_key
   ADMIN_EMAIL=admin@example.com
   ```
3. **Initialize Database**:
   Run the migration script to ensure the schema is up to date:
   ```bash
   python migrate_db.py
   ```
4. **Run Server**:
   ```bash
   python app.py
   ```
   Access at `http://localhost:8000`.

---

## 🚀 Deployment

### Deploy to Render (Recommended)
1. **Fork/Push** this repository to GitHub.
2. **Connect to Render**: Create a new "Web Service" and select your repository.
3. **Configuration**: Render will automatically detect the `render.yaml` file.
4. **Environment Variables**: Add your `GROQ_API_KEY` and `ADMIN_EMAIL` in the Render dashboard under the "Environment" tab.
5. **Persistent Disk**: Since this app uses SQLite, it is recommended to add a **Persistent Disk** to your Render service and update the `SQLALCHEMY_DATABASE_URI` to point to the disk path if you want to keep data across redeploys.

### Deploy via Docker
1. **Build Image**:
   ```bash
   docker build -t skillforge-ai .
   ```
2. **Run Container**:
   ```bash
   docker run -p 8000:8000 --env-file .env skillforge-ai
   ```

---

## 🔒 Privacy & Ethics
- **Client-Side AI**: Proctoring (face detection) is performed locally in the browser to ensure user privacy.
- **Data Security**: Passwords and sensitive session data are encrypted using enterprise-standard hashing.
