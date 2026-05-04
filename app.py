from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
from flask_cors import CORS
from groq import Groq
import os, uuid, json, re
from datetime import datetime
from database import db, User, Conversation, Message, InterviewSession, QuizResult, CareerRoadmap, CheatLog
import base64
from dotenv import load_dotenv
from functools import wraps
from whitenoise import WhiteNoise

load_dotenv()

app = Flask(__name__)
app.wsgi_app = WhiteNoise(app.wsgi_app, root='static/') # Serve static files if needed
app.secret_key = os.getenv("FLASK_SECRET_KEY", "skillforge-ai-secret-dev")
CORS(app)

@app.route("/health")
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()}), 200

# Force absolute path for SQLite to avoid confusion with multiple instance folders
db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance")
db_path = os.path.join(db_dir, "skillforge.db")
if not os.path.exists(db_dir):
    os.makedirs(db_dir)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024   # 5 MB upload limit
db.init_app(app)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

# ── System prompts ─────────────────────────────────────────────────────────────

TUTOR_PROMPTS = {
    "normal": (
        "You are SkillForge AI, a smart and friendly AI tutor for students and job seekers. "
        "Answer clearly with examples. Keep focused (3–5 sentences unless more depth is needed). "
        "After answering, suggest one follow-up topic."
    ),
    "eli5": (
        "You are SkillForge AI. Explain like the student is 5 years old. "
        "Simple words, fun real-life analogies, zero jargon. Max 5 sentences."
    ),
    "exam": (
        "You are SkillForge AI in exam mode. SHORT, precise, exam-ready answers. "
        "Format: 1-line definition, then 2–3 bullet points. Max 6 lines. No fluff."
    ),
}

INTERVIEW_SYSTEM = """You are an expert AI interviewer conducting a mock interview.
You have been given the candidate's profile: name, role they're applying for, and skills/background.

RULES:
1. Ask ONE question at a time — never multiple questions together.
2. After the candidate answers, give structured feedback IMMEDIATELY in this exact JSON format:
{
  "feedback": {
    "content_score": <1-10>,
    "confidence_score": <1-10>,
    "content_feedback": "<2-3 sentences on answer quality>",
    "suggestion": "<1 specific improvement tip>",
    "follow_up": "<one natural follow-up question OR null if moving to next topic>"
  },
  "next_question": "<the next interview question OR 'INTERVIEW_COMPLETE' if done>"
}
3. Vary question types: HR, Technical, Behavioral (STAR method).
4. After 8–10 questions, set next_question to "INTERVIEW_COMPLETE".
5. Always respond with ONLY the JSON — no extra text outside the JSON."""

SCORE_SYSTEM = """You are an expert interview coach. 
Analyze the complete interview transcript provided and return ONLY this JSON:
{
  "scores": {
    "communication": <1-10>,
    "technical": <1-10>,
    "behavioral": <1-10>,
    "confidence": <1-10>,
    "overall": <1-10>
  },
  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "improvements": ["<area 1>", "<area 2>", "<area 3>"],
  "verdict": "<2-3 sentence overall assessment>",
  "hire_recommendation": "<Strong Yes / Yes / Maybe / No>"
}"""

RESUME_SYSTEM = """Extract key information from this resume/profile text and return ONLY this JSON:
{
  "name": "<candidate name or Unknown>",
  "role": "<most recent or target role>",
  "skills": ["<skill1>", "<skill2>", "<skill3>", ...],
  "experience_years": <number or 0>,
  "summary": "<2-3 sentence professional summary>"
}"""

QUIZ_SYSTEM = """You are an Adaptive Learning Quiz engine.
Your goal is to generate 10 multiple-choice questions for a student.

INPUT:
1. Topic: The main subject.
2. Weak Areas: A list of topics the student struggled with previously.
3. Difficulty: The difficulty level of the quiz (Moderate or Hard).

RULES:
1. Focus 60-70% of questions on the provided Weak Areas if they exist.
2. Ensure the questions match the specified Difficulty level.
3. Return ONLY a JSON object with this structure:
{
  "topic": "Main Topic",
  "difficulty": "Moderate/Hard",
  "questions": [
    {
      "id": 1,
      "question": "Text of the question",
      "options": ["A", "B", "C", "D"],
      "answer": 0,
      "explanation": "Brief explanation",
      "tags": ["subtopic1", "subtopic2"]
    }
  ]
}"""

ROADMAP_SYSTEM = """You are an advanced AI career coach, technical interviewer, and market analyst.
Your task is to generate a COMPLETE career evaluation and skill verification system for a user.

INPUT:
1. Target Role: e.g., SDE, Data Scientist.
2. User Skill Level: beginner/intermediate/advanced.
3. User Skills: List of current skills.
4. Weak Skills (if available): List of weak topics.
5. Job Market Skills Data: Trending skills for the role.

OUTPUT FORMAT (Strict JSON):
Return ONLY a valid JSON object with the following structure:
{
  "market_alignment": {
    "match_percentage": 85,
    "strong_skills": ["Skill A", "Skill B"],
    "missing_critical_skills": ["Skill C"],
    "emerging_skills": ["Skill D"],
    "top_3_priority": ["Skill E", "Skill F", "Skill G"],
    "readiness": "Beginner/Job-Ready/Competitive",
    "suggestions": ["Suggestion 1", "Suggestion 2"]
  },
  "skill_verification": {
    "title": "Challenge Title",
    "scenario": "Real-world job scenario",
    "problem": "Clear practical problem statement",
    "constraints": ["Constraint 1"],
    "expected_output": "What the user should produce",
    "evaluation_criteria": [{"criterion": "Name", "score": 20}],
    "hidden_test_cases": ["Case 1"],
    "difficulty_justification": "Why it matches user level"
  },
  "anti_cheat_oral": [
    {"question": "Why...", "type": "Why"},
    {"question": "What if...", "type": "What if"},
    {"question": "Deep dive...", "type": "Conceptual"}
  ],
  "evaluation_logic": {
    "strong_indicators": ["Indicator 1"],
    "weak_indicators": ["Indicator 1"],
    "cheat_signs": ["Sign 1"],
    "scoring_logic": "How to score 0-100",
    "criteria": {
      "genuine": "Description",
      "partial": "Description",
      "cheated": "Description"
    }
  },
  "roadmap": [
    {
      "week": 1,
      "focus": "Topic",
      "tasks": ["Task 1"],
      "resources": [{"name": "Name", "url": "Link"}]
    }
  ]
}

RULES:
1. Generate an intensive 4-week roadmap alongside the evaluation.
2. If Weak Skills are provided, prioritize them for the verification challenge.
3. Be concise, structured, and practical. Avoid generic content.
4. Everything must feel like real industry tasks.
5. Ensure difficulty matches user level.
6. Return ONLY valid JSON."""

WEAK_KEYWORDS = [
    "recursion","big-o","big o","pointers","dynamic programming",
    "normalization","joins","sql","deadlock","semaphore",
    "calculus","integration","differentiation","matrices",
    "linked list","binary tree","graph","sorting","hashing","heap",
    "networking","tcp","http","dns","osi",
]

def detect_weak(text):
    found, lower = [], text.lower()
    for kw in WEAK_KEYWORDS:
        if kw in lower and kw not in found:
            found.append(kw)
    return found[:3]

def ai_call(messages, system, temperature=0.7, max_tokens=2048):
    """Call Groq API."""
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role":"system","content":system}] + messages,
            max_tokens=max_tokens, temperature=temperature,
        )
        if not resp.choices:
            print("DEBUG: Groq API returned no choices")
            return None
        return resp.choices[0].message.content
    except Exception as e:
        print(f"DEBUG: Groq API Error: {str(e)}")
        raise e

def safe_json(text):
    """Extract JSON from LLM response even if it has extra text or minor malformations."""
    if not text:
        return None
    
    # Remove markdown code block artifacts
    text = re.sub(r'```(?:json)?\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    
    # Try to find JSON block by finding first { and last }
    start = text.find('{')
    end = text.rfind('}')
    
    if start != -1 and end != -1:
        json_str = text[start:end+1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"DEBUG: Initial JSON parse failed: {e}")
            # Attempt recovery for common issues
            try:
                # 1. Remove trailing commas before closing braces/brackets
                fixed_json = re.sub(r',\s*([}\]])', r'\1', json_str)
                # 2. Try to fix escaped characters if the AI incorrectly double-escaped
                # fixed_json = fixed_json.encode('utf-8').decode('unicode_escape')
                return json.loads(fixed_json)
            except Exception as e2:
                print(f"DEBUG: JSON recovery failed: {e2}")
                print(f"DEBUG: Malformed JSON snippet: {json_str[:200]}...")
    
    print(f"DEBUG: No valid JSON object found in text: {text[:200]}...")
    return None

# ── Helpers ────────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login_page"))
        
        user = User.query.get(session["user_id"])
        
        if not user or not user.is_admin:
            return jsonify({"error": "Access Denied: Admin privileges required"}), 403
        return f(*args, **kwargs)
    return decorated_function

def get_uid():
    return session.get("user_id")

# ══════════════════════════════════════════════════════════════════════════════
# ROUTES — AUTH
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        data = request.form
        username = data.get("username")
        password = data.get("password")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session["user_id"] = str(user.id)
            session["username"] = user.username
            return redirect(url_for("index"))
        flash("Invalid username or password")
    return render_template("login.html", mode="login")

@app.route("/signup", methods=["GET", "POST"])
def signup_page():
    if request.method == "POST":
        data = request.form
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")
        full_name = data.get("full_name")
        
        if User.query.filter_by(username=username).first():
            flash("Username already exists")
        elif User.query.filter_by(email=email).first():
            flash("Email already registered")
        else:
            admin_email = os.getenv("ADMIN_EMAIL", "admin@careerpath.ai")
            is_admin = (email == admin_email)
            new_user = User(username=username, email=email, full_name=full_name, is_admin=is_admin)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            session["user_id"] = str(new_user.id)
            session["username"] = new_user.username
            return redirect(url_for("index"))
    return render_template("login.html", mode="signup")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))

@app.route("/api/profile")
@login_required
def get_profile():
    uid = get_uid()
    user = User.query.get(int(uid))
    if not user: return jsonify({"error": "User not found"}), 404

    return jsonify({
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "bio": user.bio,
        "created_at": user.created_at.isoformat(),
        "is_admin": user.is_admin
    })

@app.route("/api/profile/update", methods=["POST"])
@login_required
def update_profile():
    uid = get_uid()
    user = User.query.get(int(uid))
    data = request.get_json()
    user.full_name = data.get("full_name", user.full_name)
    user.bio = data.get("bio", user.bio)
    db.session.commit()
    return jsonify({"status": "success"})

# ══════════════════════════════════════════════════════════════════════════════
# ROUTES — PAGES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/interview")
@login_required
def interview_page():
    return render_template("interview.html")

# ══════════════════════════════════════════════════════════════════════════════
# ROUTES — TUTOR API
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/ask", methods=["POST"])
@login_required
def ask():
    data       = request.get_json()
    question   = data.get("question","").strip()
    mode       = data.get("mode","normal")
    convo_id   = data.get("conversation_id")
    uid        = get_uid()

    if not question: return jsonify({"error":"Question required"}), 400
    if mode not in TUTOR_PROMPTS: mode = "normal"

    convo = Conversation.query.filter_by(id=convo_id, user_id=uid).first() if convo_id else None
    if not convo:
        convo = Conversation(user_id=uid, title=question[:60])
        db.session.add(convo); db.session.flush()
        convo_id = convo.id

    history = Message.query.filter_by(conversation_id=convo_id)\
        .order_by(Message.created_at.asc()).limit(10).all()
    messages = [{"role":m.role,"content":m.content} for m in history]
    messages.append({"role":"user","content":question})

    db.session.add(Message(conversation_id=convo_id, role="user", content=question, mode=mode))

    try:
        answer = ai_call(messages, TUTOR_PROMPTS[mode])
    except Exception as e:
        db.session.rollback()
        return jsonify({"error":str(e)}), 500

    db.session.add(Message(conversation_id=convo_id, role="assistant", content=answer, mode=mode))
    db.session.commit()

    return jsonify({
        "answer": answer,
        "conversation_id": convo_id,
        "weak_topics": detect_weak(question),
        "mode": mode,
        "timestamp": datetime.utcnow().isoformat(),
    })

@app.route("/api/history")
@login_required
def history():
    uid = get_uid()
    convos = Conversation.query.filter_by(user_id=uid)\
        .order_by(Conversation.created_at.desc()).limit(15).all()
    return jsonify([{"id":c.id,"title":c.title,"created_at":c.created_at.isoformat()} for c in convos])

@app.route("/api/conversation/<int:cid>")
@login_required
def get_conversation(cid):
    uid = get_uid()
    convo = Conversation.query.filter_by(id=cid, user_id=uid).first()
    if not convo: return jsonify({"error":"Not found"}), 404
    msgs = Message.query.filter_by(conversation_id=cid).order_by(Message.created_at.asc()).all()
    return jsonify({"id":convo.id,"title":convo.title,
        "messages":[{"role":m.role,"content":m.content,"mode":m.mode} for m in msgs]})

@app.route("/api/weak-topics")
@login_required
def weak_topics():
    uid = get_uid()
    convos = Conversation.query.filter_by(user_id=uid).all()
    ids = [c.id for c in convos]
    if not ids: return jsonify({"weak":[],"strong":[]})
    questions = Message.query.filter(
        Message.conversation_id.in_(ids), Message.role=="user").all()
    freq = {}
    for m in questions:
        for kw in detect_weak(m.content): freq[kw] = freq.get(kw,0)+1
    s = sorted(freq.items(), key=lambda x:x[1], reverse=True)
    return jsonify({"weak":[t[0] for t in s[:3]],"strong":[t[0] for t in s[3:6]]})

# ══════════════════════════════════════════════════════════════════════════════
# ROUTES — INTERVIEW API
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/interview/start", methods=["POST"])
@login_required
def interview_start():
    """
    Body: { name, role, skills, interviewer_mode }
    Returns: { session_id, first_question }
    """
    data = request.get_json()
    name  = data.get("name","Candidate").strip()
    role  = data.get("role","Software Engineer").strip()
    skills = data.get("skills","").strip()
    imode  = data.get("interviewer_mode","friendly")  # friendly | strict
    uid   = get_uid()

    profile = f"Candidate: {name}\nRole: {role}\nSkills/Background: {skills}"
    style   = "Be encouraging and supportive." if imode=="friendly" else \
              "Be direct, challenging, and professional. Push back on weak answers."

    system = INTERVIEW_SYSTEM + f"\n\nINTERVIEWER STYLE: {style}"

    # Ask AI for first question
    try:
        raw = ai_call(
            [{"role":"user","content":f"Start the interview. Profile:\n{profile}\n\nAsk the first question."}],
            system, temperature=0.8
        )
    except Exception as e:
        return jsonify({"error":str(e)}), 500

    parsed = safe_json(raw)
    first_q = parsed.get("next_question","Tell me about yourself.") if parsed else "Tell me about yourself."

    sess = InterviewSession(
        user_id=uid, name=name, role=role, skills=skills,
        interviewer_mode=imode,
        system_prompt=system,
        transcript=json.dumps([{"role":"assistant","content":first_q,"type":"question"}]),
        question_count=1,
    )
    db.session.add(sess); db.session.commit()

    return jsonify({"session_id":sess.id, "first_question":first_q, "name":name, "role":role})


@app.route("/api/interview/answer", methods=["POST"])
@login_required
def interview_answer():
    """
    Body: { session_id, answer }
    Returns: { feedback, next_question, is_complete, question_number }
    """
    data = request.get_json()
    sid    = data.get("session_id")
    answer = data.get("answer","").strip()
    uid    = get_uid()

    sess = InterviewSession.query.filter_by(id=sid, user_id=uid).first()
    if not sess: return jsonify({"error":"Session not found"}), 404
    if not answer: return jsonify({"error":"Answer required"}), 400

    transcript = json.loads(sess.transcript)

    # Build messages for context
    messages = []
    for t in transcript:
        messages.append({"role": "assistant" if t["role"]=="assistant" else "user",
                         "content": t["content"]})
    messages.append({"role":"user","content":answer})

    try:
        raw = ai_call(messages, sess.system_prompt, temperature=0.7)
    except Exception as e:
        return jsonify({"error":str(e)}), 500

    parsed = safe_json(raw)
    if not parsed:
        # fallback
        parsed = {
            "feedback": {
                "content_score":7,"confidence_score":7,
                "content_feedback":"Good attempt. Keep elaborating with examples.",
                "suggestion":"Use the STAR method for structured answers.",
                "follow_up": None
            },
            "next_question": "Can you tell me about a challenging project you worked on?"
        }

    feedback    = parsed.get("feedback",{})
    next_q      = parsed.get("next_question","INTERVIEW_COMPLETE")
    is_complete = next_q == "INTERVIEW_COMPLETE"

    # Update transcript
    transcript.append({"role":"user","content":answer,"type":"answer"})
    if not is_complete:
        q_text = feedback.get("follow_up") or next_q
        transcript.append({"role":"assistant","content":q_text,"type":"question"})
    
    sess.transcript     = json.dumps(transcript)
    sess.question_count = sess.question_count + 1
    if is_complete: sess.completed = True
    db.session.commit()

    return jsonify({
        "feedback": feedback,
        "next_question": feedback.get("follow_up") or next_q,
        "is_complete": is_complete,
        "question_number": sess.question_count,
    })


@app.route("/api/interview/score/<int:sid>")
@login_required
def interview_score(sid):
    """Generate final score dashboard for a completed interview."""
    uid  = get_uid()
    sess = InterviewSession.query.filter_by(id=sid, user_id=uid).first()
    if not sess: return jsonify({"error":"Not found"}), 404

    transcript = json.loads(sess.transcript)
    transcript_text = "\n".join(
        f"[{'INTERVIEWER' if t['role']=='assistant' else 'CANDIDATE'}]: {t['content']}"
        for t in transcript
    )

    try:
        raw = ai_call(
            [{"role":"user","content":f"Role applied for: {sess.role}\n\nTranscript:\n{transcript_text}"}],
            SCORE_SYSTEM, temperature=0.3
        )
    except Exception as e:
        return jsonify({"error":str(e)}), 500

    result = safe_json(raw)
    if not result:
        result = {
            "scores":{"communication":7,"technical":7,"behavioral":7,"confidence":7,"overall":7},
            "strengths":["Good communication","Relevant experience","Enthusiasm"],
            "improvements":["Add more specific examples","Improve technical depth","Practice STAR method"],
            "verdict":"Solid candidate with room for improvement.",
            "hire_recommendation":"Maybe"
        }

    return jsonify({**result, "name":sess.name, "role":sess.role,
                    "question_count":sess.question_count})


@app.route("/api/interview/parse-resume", methods=["POST"])
@login_required
def parse_resume():
    """Parse plain-text resume pasted by user."""
    data = request.get_json()
    text = data.get("text","").strip()
    if not text: return jsonify({"error":"No text provided"}), 400

    try:
        raw = ai_call(
            [{"role":"user","content":f"Parse this resume:\n\n{text}"}],
            RESUME_SYSTEM, temperature=0.3
        )
    except Exception as e:
        return jsonify({"error":str(e)}), 500

    result = safe_json(raw)
    return jsonify(result or {"name":"","role":"","skills":[],"summary":""})


@app.route("/api/interview/sessions")
@login_required
def interview_sessions():
    uid = get_uid()
    sessions = InterviewSession.query.filter_by(user_id=uid)\
        .order_by(InterviewSession.created_at.desc()).limit(10).all()
    return jsonify([{
        "id":s.id,"name":s.name,"role":s.role,
        "completed":s.completed,"question_count":s.question_count,
        "created_at":s.created_at.isoformat()
    } for s in sessions])

# ══════════════════════════════════════════════════════════════════════════════
# ROUTES — ADAPTIVE LEARNING (QUIZ)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/quiz/generate", methods=["POST"])
@login_required
def generate_quiz():
    data = request.get_json()
    topic = data.get("topic", "General Computer Science")
    difficulty = data.get("difficulty", "Moderate")
    uid = get_uid()
    
    # Get previous weak areas
    try:
        prev_results = QuizResult.query.filter_by(user_id=uid).order_by(QuizResult.created_at.desc()).limit(3).all()
        weak_areas = []
        for r in prev_results:
            try:
                wa = json.loads(r.weak_areas)
                if isinstance(wa, list):
                    weak_areas.extend(wa)
            except:
                pass
        
        prompt = f"Topic: {topic}\nDifficulty: {difficulty}\nWeak Areas from previous sessions: {list(set(weak_areas))}"
        
        raw = ai_call([{"role": "user", "content": prompt}], QUIZ_SYSTEM, temperature=0.5, max_tokens=1500)
        quiz = safe_json(raw)
        if not quiz: 
            print(f"DEBUG: Failed to parse quiz JSON from raw response: {raw}")
            return jsonify({"error": "Failed to generate valid quiz format. Please try again."}), 500
        return jsonify(quiz)
    except Exception as e:
        print(f"DEBUG: Quiz generation error: {str(e)}")
        return jsonify({"error": f"Server error during quiz generation: {str(e)}"}), 500

@app.route("/api/quiz/submit", methods=["POST"])
@login_required
def submit_quiz():
    data = request.get_json()
    uid = get_uid()
    topic = data.get("topic")
    difficulty = data.get("difficulty", "Moderate")
    score = data.get("score")
    total = data.get("total")
    weak_areas = data.get("weak_areas", []) # tags of failed questions
    
    # Also extract strong areas (all tags from questions where user got it right)
    all_questions = data.get("all_questions", [])
    strong_areas = []
    failed_indices = data.get("failed_indices", [])
    
    for idx, q in enumerate(all_questions):
        if idx not in failed_indices:
            strong_areas.extend(q.get("tags", []))
            
    result = QuizResult(
        user_id=uid,
        topic=topic,
        difficulty=difficulty,
        score=score,
        total=total,
        weak_areas=json.dumps(weak_areas)
    )
    db.session.add(result)
    db.session.commit()
    return jsonify({"status": "success", "id": result.id})

@app.route("/api/quiz/stats")
@login_required
def quiz_stats():
    uid = get_uid()
    results = QuizResult.query.filter_by(user_id=uid).order_by(QuizResult.created_at.desc()).all()
    
    topic_scores = {} # topic -> [scores]
    weak_counts = {} # tag -> count
    
    for r in results:
        # History
        if r.topic not in topic_scores: topic_scores[r.topic] = []
        topic_scores[r.topic].append({
            "score": r.score,
            "total": r.total,
            "date": r.created_at.isoformat()
        })
        
        # Weak areas
        try:
            wa = json.loads(r.weak_areas)
            for tag in wa:
                weak_counts[tag] = weak_counts.get(tag, 0) + 1
        except: pass

    # Sort weak areas by frequency
    sorted_weak = sorted(weak_counts.items(), key=lambda x: x[1], reverse=True)
    
    return jsonify({
        "history": topic_scores,
        "weak_topics": [{"topic": t, "count": c} for t, c in sorted_weak[:5]],
        "overall_avg": sum([r.score for r in results]) / sum([r.total for r in results]) if results else 0
    })

# ══════════════════════════════════════════════════════════════════════════════
# ROUTES — AI CAREER COACH (ROADMAP)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/roadmap/generate", methods=["POST"])
@login_required
def generate_roadmap():
    uid = get_uid()
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        role = data.get("role")
        level = data.get("level", "beginner")
        skills = data.get("skills", [])
        
        if not role:
            return jsonify({"error": "Target role is required"}), 400
        
        # Ensure skills is a list
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(',') if s.strip()]
        elif not isinstance(skills, list):
            skills = []
            
        # Get weak skills from DB (Quiz Results)
        quiz_results = QuizResult.query.filter_by(user_id=uid).all()
        weak_skills_set = set()
        for qr in quiz_results:
            try:
                wa = json.loads(qr.weak_areas)
                if isinstance(wa, list):
                    for skill in wa:
                        weak_skills_set.add(skill)
            except:
                pass
        weak_skills = list(weak_skills_set)
        
        # Mock market data (could be expanded later)
        market_data = "AI, Cloud Computing, Data Analytics, DevOps, Cyber Security"
        
        prompt = (
            f"Target Role: {role}\n"
            f"User Skill Level: {level}\n"
            f"User Skills: {', '.join(skills) if skills else 'None'}\n"
            f"Weak Skills: {', '.join(weak_skills) if weak_skills else 'None'}\n"
            f"Job Market Data: {market_data}"
        )
        
        # Increase max_tokens for advanced output
        try:
            raw = ai_call([{"role": "user", "content": prompt}], ROADMAP_SYSTEM, temperature=0.4, max_tokens=4000)
            print(f"DEBUG: AI Raw Response for Roadmap received. Length: {len(raw) if raw else 0}")
        except Exception as ai_err:
            print(f"DEBUG: AI Call failed for Roadmap: {ai_err}")
            return jsonify({"error": f"AI service unavailable: {str(ai_err)}"}), 503
        
        if not raw:
            print("DEBUG: AI returned empty response")
            return jsonify({"error": "AI returned empty response. Please try again."}), 500
            
        roadmap_data = safe_json(raw)
        if not roadmap_data:
            print(f"DEBUG: Failed to parse roadmap JSON. Raw response: {raw}")
            return jsonify({
                "error": "Failed to generate a valid roadmap format. Please try again.",
                "details": "AI response was not in expected JSON format."
            }), 500
        
        # Save roadmap
        try:
            saved = CareerRoadmap(
                user_id=uid,
                target_role=role,
                skills=json.dumps(skills),
                roadmap_json=json.dumps(roadmap_data)
            )
            db.session.add(saved)
            db.session.commit()
            print(f"DEBUG: Roadmap saved to database. ID: {saved.id}")
        except Exception as db_err:
            print(f"DEBUG: Database error saving roadmap: {db_err}")
            db.session.rollback()
            return jsonify({"error": f"Database error: {str(db_err)}"}), 500
        
        return jsonify(roadmap_data)
    except Exception as e:
        import traceback
        print(f"DEBUG: Roadmap generation exception: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/roadmap/history")
@login_required
def roadmap_history():
    uid = get_uid()
    roadmaps = CareerRoadmap.query.filter_by(user_id=uid).order_by(CareerRoadmap.created_at.desc()).all()
    return jsonify([{
        "id": r.id,
        "role": r.target_role,
        "created_at": r.created_at.isoformat()
    } for r in roadmaps])

@app.route("/api/roadmap/<int:rid>")
@login_required
def get_roadmap(rid):
    uid = get_uid()
    r = CareerRoadmap.query.filter_by(id=rid, user_id=uid).first()
    if not r: return jsonify({"error": "Not found"}), 404
    return jsonify(json.loads(r.roadmap_json))

# ══════════════════════════════════════════════════════════════════════════════
# ROUTES — ANTI-CHEAT
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/anticheat/log-violation", methods=["POST"])
@login_required
def log_violation():
    uid = get_uid()
    data = request.get_json()
    violation = data.get("violation")
    details = data.get("details", "")
    
    log = CheatLog(user_id=uid, violation=violation, details=details)
    db.session.add(log)
    db.session.commit()
    return jsonify({"status": "logged"})

@app.route("/api/anticheat/snapshot", methods=["POST"])
@login_required
def verify_face():
    uid = get_uid()
    data = request.get_json()
    image_data = data.get("image") # base64
    is_reference = data.get("is_reference", False)
    
    if not image_data: return jsonify({"error": "No image provided"}), 400
    
    # In a real app, we'd save the reference photo and compare subsequent ones
    # For now, let's store/update the reference in session or a temporary file
    # This is a simplified implementation for the task
    
    img_bytes = base64.b64decode(image_data.split(",")[1])
    
    # Save the snapshot
    user_dir = os.path.join("snapshots", str(uid))
    os.makedirs(user_dir, exist_ok=True)
    
    filename = "reference.jpg" if is_reference else f"snap_{int(datetime.utcnow().timestamp())}.jpg"
    filepath = os.path.join(user_dir, filename)
    
    with open(filepath, "wb") as f:
        f.write(img_bytes)
    
    if is_reference:
        return jsonify({"status": "reference_captured"})
    
    # Face verification logic (mocked if deepface is not available)
    try:
        from deepface import DeepFace
        ref_path = os.path.join(user_dir, "reference.jpg")
        if not os.path.exists(ref_path):
            return jsonify({"status": "no_reference_to_compare"})
            
        # enforce_detection=True will raise an exception if no face is found
        try:
            result = DeepFace.verify(img1_path=filepath, img2_path=ref_path, enforce_detection=True)
            verified = result.get("verified", False)
        except ValueError:
            # No face detected in one of the images
            log = CheatLog(user_id=uid, violation="No Face Detected", details="Webcam could not detect a face. Possible hiding or phone usage.")
            db.session.add(log)
            db.session.commit()
            return jsonify({"status": "no_face", "verified": False})
            
        if not verified:
            log = CheatLog(user_id=uid, violation="Face Mismatch", details=f"Similarity distance: {result.get('distance')}")
            db.session.add(log)
            db.session.commit()
            
        return jsonify({"status": "verified" if verified else "mismatch", "verified": verified})
    except ImportError:
        # Fallback if deepface is not installed
        return jsonify({"status": "verified_mock", "verified": True, "note": "DeepFace not installed"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Recruiter Dashboard (B2B) ──────────────────────────────────────────────────

@app.route("/api/recruiter/candidates")
@admin_required
def recruiter_candidates():
    # In a real app, we'd check if current_user.role == 'recruiter'
    users = User.query.all()
    reports = []
    
    for user in users:
        # Calculate Verified Skill Score (avg of all quiz results)
        quizzes = QuizResult.query.filter_by(user_id=user.id).all()
        total_score = sum([q.score for q in quizzes if q.score is not None])
        total_possible = sum([q.total for q in quizzes if q.total is not None])
        skill_score = round((total_score / total_possible * 100), 1) if total_possible > 0 else 0
        
        # Calculate Cheat Probability Score
        violations = CheatLog.query.filter_by(user_id=user.id).all()
        # Heuristic: More violations + specific types (Proctoring) increase score
        base_prob = len(violations) * 5
        proctor_violations = len([v for v in violations if v.violation == "Proctoring"])
        cheat_prob = min(base_prob + (proctor_violations * 10), 100)
        
        # Get latest roadmap/role
        latest_roadmap = CareerRoadmap.query.filter_by(user_id=user.id).order_by(CareerRoadmap.created_at.desc()).first()
        target_role = latest_roadmap.target_role if latest_roadmap else "N/A"
        
        reports.append({
            "id": user.id,
            "username": user.username or "Unknown",
            "target_role": target_role,
            "skill_score": skill_score,
            "cheat_probability": cheat_prob,
            "total_quizzes": len(quizzes),
            "total_violations": len(violations)
        })
        
    return jsonify(reports)

@app.route("/api/recruiter/candidate/<int:user_id>")
@admin_required
def recruiter_candidate_detail(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "Candidate not found"}), 404
            
        quizzes = QuizResult.query.filter_by(user_id=user_id).order_by(QuizResult.created_at.desc()).all()
        violations = CheatLog.query.filter_by(user_id=user_id).order_by(CheatLog.created_at.desc()).all()
        roadmaps = CareerRoadmap.query.filter_by(user_id=user_id).order_by(CareerRoadmap.created_at.desc()).all()
        
        return jsonify({
            "username": user.username or "Unknown",
            "email": user.email,
            "quizzes": [{
                "topic": q.topic or "N/A",
                "score": q.score if q.score is not None else 0,
                "total": q.total if q.total is not None else 0,
                "difficulty": q.difficulty or "N/A",
                "date": q.created_at.isoformat() if q.created_at else datetime.now().isoformat()
            } for q in quizzes],
            "violations": [{
                "type": v.violation or "Unknown",
                "details": v.details or "",
                "date": v.created_at.isoformat() if v.created_at else datetime.now().isoformat()
            } for v in violations],
            "roadmaps": [{
                "role": r.target_role or "N/A",
                "date": r.created_at.isoformat() if r.created_at else datetime.now().isoformat()
            } for r in roadmaps]
        })
    except Exception as e:
        print(f"DEBUG: Error in candidate detail for ID {user_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.errorhandler(500)
def internal_error(error):
    import traceback
    print("DEBUG: 500 ERROR DETECTED")
    traceback.print_exc()
    return jsonify({"error": "Internal Server Error", "details": str(error)}), 500

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)