from flask import Flask, request, render_template, redirect, session, jsonify, flash
import pdfplumber
import docx
import mysql.connector
import os
from werkzeug.utils import secure_filename
import json
from datetime import timedelta
import pandas as pd

app = Flask(__name__)
app.secret_key = "placement_portal_secret"
app.permanent_session_lifetime = timedelta(days=30)

@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    return r


#MYSQL Connection
def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Hasini@1234",
        database="placement_portal2",
        connection_timeout=30,
        autocommit=False
    )

db = get_connection()
cursor = db.cursor(dictionary=True)

def ensure_connection():
    """Auto-reconnect if MySQL connection has gone away."""
    global db, cursor
    try:
        db.ping(reconnect=True, attempts=3, delay=1)
        if not cursor or cursor._connection is None:
            cursor = db.cursor(dictionary=True)
    except Exception:
        try:
            db = get_connection()
            cursor = db.cursor(dictionary=True)
        except Exception as e:
            print("DB reconnect failed:", e)

# Database Tables & Mock Data Initialization
def init_database():
    ensure_connection()
    try:
        # Create students table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                student_id INT PRIMARY KEY,
                name VARCHAR(50),
                email VARCHAR(100),
                password VARCHAR(50),
                branch VARCHAR(50),
                cgpa FLOAT,
                backlogs INT,
                skills TEXT,
                selected_tier INT DEFAULT NULL,
                batch INT,
                roll_number VARCHAR(50) DEFAULT NULL,
                phone_number VARCHAR(20) DEFAULT NULL,
                aadhar VARCHAR(20) DEFAULT NULL,
                pan VARCHAR(20) DEFAULT NULL
            )
        """)
       
        try:
            cursor.execute("ALTER TABLE students ADD COLUMN profile_photo VARCHAR(255) DEFAULT '/static/default_avatar.png'")
        except Exception:
            pass
           
        for col_sql in [
            "ALTER TABLE students ADD COLUMN roll_number VARCHAR(50) DEFAULT NULL",
            "ALTER TABLE students ADD COLUMN phone_number VARCHAR(20) DEFAULT NULL",
            "ALTER TABLE students ADD COLUMN aadhar VARCHAR(20) DEFAULT NULL",
            "ALTER TABLE students ADD COLUMN pan VARCHAR(20) DEFAULT NULL",
            "ALTER TABLE students ADD COLUMN backlog_history INT DEFAULT 0",
            "ALTER TABLE students ADD COLUMN must_change_password TINYINT(1) DEFAULT 1"
        ]:
            try:
                cursor.execute(col_sql)
            except Exception:
                pass
       
        # Create faculty table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS faculty (
                faculty_id INT PRIMARY KEY,
                name VARCHAR(50),
                email VARCHAR(100),
                password VARCHAR(50)
            )
        """)
       
        # Create recruiters table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recruiters (
                recruiter_id INT PRIMARY KEY,
                company_name VARCHAR(50),
                email VARCHAR(100),
                password VARCHAR(50)
            )
        """)
       
        # Create jobs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                job_id VARCHAR(30) UNIQUE,
                company_name VARCHAR(100),
                role VARCHAR(100),
                ctc VARCHAR(30),
                location VARCHAR(100),
                bond VARCHAR(50) DEFAULT 'None',
                cgpa_cutoff DECIMAL(4,2) DEFAULT 0.0,
                active_backlogs INT DEFAULT 0,
                backlog_history INT DEFAULT 0,
                branches TEXT,
                tier VARCHAR(20) DEFAULT 'Tier 1',
                description TEXT,
                req_aadhar TINYINT(1) DEFAULT 0,
                req_pan TINYINT(1) DEFAULT 0,
                req_other VARCHAR(200),
                pdf_path VARCHAR(300),
                deadline DATETIME DEFAULT NULL
            )
        """)
       
        # Add missing columns for existing installs (including 'id' for older schemas)
        for col_sql in [
            "ALTER TABLE jobs ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY",
            "ALTER TABLE jobs ADD COLUMN ctc VARCHAR(30)",
            "ALTER TABLE jobs ADD COLUMN location VARCHAR(100)",
            "ALTER TABLE jobs ADD COLUMN bond VARCHAR(50) DEFAULT 'None'",
            "ALTER TABLE jobs ADD COLUMN cgpa_cutoff DECIMAL(4,2) DEFAULT 0.0",
            "ALTER TABLE jobs ADD COLUMN active_backlogs INT DEFAULT 0",
            "ALTER TABLE jobs ADD COLUMN backlog_history INT DEFAULT 0",
            "ALTER TABLE jobs ADD COLUMN branches TEXT",
            "ALTER TABLE jobs ADD COLUMN req_aadhar TINYINT(1) DEFAULT 0",
            "ALTER TABLE jobs ADD COLUMN req_pan TINYINT(1) DEFAULT 0",
            "ALTER TABLE jobs ADD COLUMN req_other VARCHAR(200)",
            "ALTER TABLE jobs ADD COLUMN pdf_path VARCHAR(300)",
            "ALTER TABLE jobs ADD COLUMN deadline DATETIME DEFAULT NULL"
        ]:
            try:
                cursor.execute(col_sql)
            except Exception:
                pass
       
        # Create applications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                application_id INT PRIMARY KEY,
                student_id INT,
                job_id INT,
                resume_path TEXT,
                status VARCHAR(50),
                applied_date DATE
            )
        """)
       
        try:
            cursor.execute("ALTER TABLE applications ADD COLUMN extra_details TEXT")
        except Exception:
            pass

        try:
            cursor.execute("ALTER TABLE applications MODIFY COLUMN job_id VARCHAR(30)")
        except Exception:
            pass

        # Create recruitment_rounds table (tracks number of rounds per job)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recruitment_rounds (
                id INT AUTO_INCREMENT PRIMARY KEY,
                job_id VARCHAR(30),
                num_rounds INT DEFAULT 1,
                UNIQUE KEY unique_job (job_id)
            )
        """)

        # Create round_results table (tracks per-student per-round status)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS round_results (
                id INT AUTO_INCREMENT PRIMARY KEY,
                job_id VARCHAR(30),
                student_id INT,
                round_number INT,
                result VARCHAR(20) DEFAULT 'Pending',
                UNIQUE KEY unique_round_result (job_id, student_id, round_number)
            )
        """)

        # Ensure drive_link column exists in round_results (added in v2)
        try:
            cursor.execute("ALTER TABLE round_results ADD COLUMN drive_link TEXT DEFAULT NULL")
        except Exception:
            pass

       
        # Create notifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                notif_id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT,
                message TEXT,
                link TEXT,
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
       
        # Create faculty table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS faculty (
                faculty_id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(50),
                email VARCHAR(100),
                password VARCHAR(50)
            )
        """)
       
        # Insert Dr. Shankar if not exists
        cursor.execute("SELECT COUNT(*) as count FROM faculty")
        if cursor.fetchone()["count"] == 0:
            cursor.execute("""
                INSERT INTO faculty (name, email, password)
                VALUES ('Dr. Shankar', 'drshankar@gmail.com', 'shankar123')
            """)
       
        # Check and insert default students if missing
        cursor.execute("SELECT COUNT(*) as count FROM students")
        if cursor.fetchone()["count"] == 0:
            cursor.execute("""
                INSERT INTO students (student_id, name, email, password, branch, cgpa, backlogs, skills, selected_tier, batch)
                VALUES
                (1, 'Pallavi', 'pallavi123@gmail.com', 'pallavi123', 'AI', 9.2, 0, 'Java, DSA, Full Stack Development', 1, 2028),
                (2, 'linda', 'linda123@gmail.com', 'linda123', 'CSE', 9.1, 0, 'C, CPP, HTML, CSS, MySQL', 2, 2029)
            """)
           
        # Check and insert default jobs if missing
        cursor.execute("SELECT COUNT(*) as count FROM jobs")
        if cursor.fetchone()["count"] == 0:
            cursor.execute("""
                INSERT INTO jobs (job_id, company_name, role, ctc, location, bond, cgpa_cutoff, active_backlogs, branches, tier, description)
                VALUES
                ('1', 'TCS', 'Software Developer', '7.00 LPA', 'Pune', 'None', 7.00, 0, 'AI, CSE, ECE, EEE', 'Tier 2', 'Join the TCS digital developer team to work on next-generation cloud architectures.'),
                ('2', 'Infosys', 'Specialist Programmer', '20.00 LPA', 'Bangalore', 'None', 9.50, 0, 'CSE, IT', 'Tier 1', 'High performance developer role working on core software products and algorithmic scaling.'),
                ('3', 'Wipro', 'Full Stack Developer', '8.00 LPA', 'Hyderabad', 'None', 6.50, 1, 'AI, CSE, ECE', 'Tier 2', 'Design and implement web interfaces and microservice endpoints in our digital unit.')
            """)
           
        db.commit()
        print("Database tables and mock data initialized successfully.")
    except Exception as e:
        print("Warning: Database initialization failed. Details:", e)

init_database()

def notify_students_new_job(company_name, role):
    """
    Helper function to notify all students when a new job is posted.
    Call this function from the faculty job post route.
    """
    try:
        message = f"New Job Posted: {company_name} is hiring for {role}!"
        link = "/eligible_companies"
       
        # Insert a notification for every student in the database
        cursor.execute("""
            INSERT INTO notifications (student_id, message, link)
            SELECT student_id, %s, %s FROM students
        """, (message, link))
        db.commit()
        print(f"Successfully notified students about {company_name} - {role}")
    except Exception as e:
        print("Failed to notify students:", e)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/resume_analyzer")
def resume_analyzer():
    return render_template("resume_analyzer.html")

@app.route("/upload",methods = ["POST"])
def upload():
    file = request.files.get("resume")
    filename = file.filename.lower() if file else ""
    role = request.form.get("role")
    custom_jd = request.form.get("custom_jd", "")
   
    if not role or role == "Select a job profile...":
        return "Please select a role."
   
    text = ""
   
    if filename.endswith(".pdf"):
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
   
    elif filename.endswith(".docx"):
        document = docx.Document(file)
        for para in document.paragraphs:
            text += para.text + "\n"
   
    else :
        return "Only PDF and DOCX files are allowed."
   

    role_skills = {

    "Frontend Developer": {
        "required": ["HTML", "CSS", "JavaScript"],
        "optional": ["React", "Angular", "Vue.js", "Bootstrap", "Tailwind CSS", "Git"]
    },

    "Backend Developer": {
        "required": ["Java", "MySQL", "DBMS"],
        "optional": ["Spring Boot", "REST API", "Hibernate", "Git", "Docker"]
    },

    "Full Stack Developer": {
        "required": ["HTML", "CSS", "JavaScript", "Java", "MySQL"],
        "optional": ["React", "Node.js", "Spring Boot", "MongoDB", "Git"]
    },

    "Data Analyst": {
        "required": ["Python", "SQL", "Excel"],
        "optional": ["Power BI", "Tableau", "Pandas", "NumPy", "Statistics"]
    },

    "AI/ML Engineer": {
        "required": ["Python", "Machine Learning", "Mathematics"],
        "optional": ["Pandas", "NumPy", "Scikit-learn", "TensorFlow", "PyTorch", "Deep Learning"]
    },

    "Resume Analyzer": {
        "required": ["Python", "Natural Language Processing", "Regex", "Text Parsing"],
        "optional": ["Machine Learning", "Spacy", "NLTK", "Flask"]
    }
    }
   
    if role == "Custom":
        custom_text = ""
        jd_file = request.files.get("jd_file")
        if jd_file and jd_file.filename:
            jd_filename = jd_file.filename.lower()
            if jd_filename.endswith(".pdf"):
                with pdfplumber.open(jd_file) as pdf:
                    for page in pdf.pages:
                        custom_text += page.extract_text() or ""
            elif jd_filename.endswith(".docx"):
                document = docx.Document(jd_file)
                for para in document.paragraphs:
                    custom_text += para.text + "\n"
            elif jd_filename.endswith(".txt"):
                custom_text = jd_file.read().decode('utf-8', errors='ignore')
        else:
            custom_text = custom_jd

        all_possible_skills = ["Java", "Python", "C++", "C", "HTML", "CSS", "JavaScript", "TypeScript", "React", "Angular", "Vue.js", "Node.js", "Spring Boot", "MySQL", "MongoDB", "PostgreSQL", "SQL", "DBMS", "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "Pandas", "NumPy", "Excel", "Power BI", "Tableau", "Git", "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Linux", "Data Structures", "Algorithms", "DSA", "Problem Solving", "Communication"]
        required_skills = []
        for s in all_possible_skills:
            if s.lower() in custom_text.lower():
                required_skills.append(s)
        optional_skills = []
        if not required_skills:
            required_skills = ["Problem Solving", "Communication"]
    else:
        selected_role = role_skills.get(role, {"required": ["Java", "Python", "SQL"], "optional": []})
        required_skills = selected_role["required"]
        optional_skills = selected_role["optional"]

    found_required = []
    missing_required = []

    for skill in required_skills:
        if skill.lower() in text.lower():
            found_required.append(skill)
        else :
            missing_required.append(skill)

    missing_optional = []
    found_optional = []

    for skill in optional_skills:
        if skill.lower() in text.lower():
            found_optional.append(skill)
        else :
            missing_optional.append(skill)

    required_score = (len(found_required)/ len(required_skills))* 80

    if(len(found_optional) >= 1 ):
        optional_score = 20
    else:
        optional_score = 0

    score = int(required_score + optional_score)

    suggestion = ""
    if len(found_optional) == 0:
        suggestion = f"Good ATS score. Consider learning one of : {optional_skills}"
    elif score < 70:
        suggestion = f"Improve required skills<br> Required skills are : {required_skills}"
    else :
        suggestion = "Strong profile for this role"

    genome_score = 0

    if score >= 70 :
        genome_score += 40
    elif score >= 50 :
        genome_score += 25
    else:
        genome_score += 10

    if "project" in text.lower() or "projects" in text.lower():
        genome_score += 20

    if "b.tech" in text.lower() or "bachelor" in text.lower() or "education" in text.lower():
        genome_score += 15
   
    if "certificate" in text.lower() or "certificates" in text.lower() or "certification" in text.lower():
        genome_score += 10
   
    if "internship" in text.lower() or "experience" in text.lower():
        genome_score += 10
   
    if "award" in text.lower() or "achievement" in text.lower():
        genome_score += 5


    final_score = int((score + genome_score) / 2)
   
    # Update student's skills and save score if logged in
    if "student_id" in session:
        student_id = session["student_id"]
        session["resume_score"] = final_score
       
        # Combine found skills
        found_skills = list(set(found_required + found_optional))
        if found_skills:
            cursor.execute("SELECT skills FROM students WHERE student_id = %s", (student_id,))
            current_skills_row = cursor.fetchone()
            existing_skills = [s.strip() for s in current_skills_row["skills"].split(",")] if current_skills_row and current_skills_row["skills"] else []
            combined_skills = list(set(existing_skills + found_skills))
            skills_str = ", ".join(combined_skills)
           
            cursor.execute("UPDATE students SET skills = %s WHERE student_id = %s", (skills_str, student_id))
            db.commit()

    found_req_str = ", ".join(found_required) if found_required else "None"
    missing_req_str = ", ".join(missing_required) if missing_required else "None"
    found_opt_str = ", ".join(found_optional) if found_optional else "None"
    missing_opt_str = ", ".join(missing_optional) if missing_optional else "None"

    return f"""
    <html>
    <head>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="/static/css/style.css">
        <title>Resume Analysis Results</title>
        <style>
            body {{
                background: linear-gradient(135deg, #0f172a, #1e293b);
                color: #f8fafc;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            .results-card {{
                background: rgba(30, 41, 59, 0.7);
                backdrop-filter: blur(16px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 24px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
                padding: 40px;
                width: 100%;
                max-width: 700px;
            }}
            .skill-box {{
                background: rgba(15, 23, 42, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                padding: 15px;
                height: 100%;
            }}
            .score-circle {{
                width: 110px;
                height: 110px;
                border-radius: 50%;
                border: 4px solid var(--accent);
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                margin: 0 auto;
                box-shadow: 0 0 15px var(--accent-glow);
            }}
        </style>
    </head>
    <body>
        <div class="results-card text-center animated-fade-in-up">
            <h2 class="mb-4 text-warning" style="font-family: var(--font-heading);">Resume Analysis Report</h2>
            <p class="text-muted mb-4">Role: <strong>{role}</strong></p>
           
            <div class="row g-3 text-start mb-4">
                <div class="col-md-6">
                    <div class="skill-box">
                        <strong class="text-success">✔ Required Skills Found</strong>
                        <p class="mb-0 text-white-50 mt-1">{found_req_str}</p>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="skill-box">
                        <strong class="text-danger">✖ Required Skills Missing</strong>
                        <p class="mb-0 text-white-50 mt-1">{missing_req_str}</p>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="skill-box">
                        <strong class="text-success">✔ Optional Skills Found</strong>
                        <p class="mb-0 text-white-50 mt-1">{found_opt_str}</p>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="skill-box">
                        <strong class="text-warning">⚠ Optional Skills Missing</strong>
                        <p class="mb-0 text-white-50 mt-1">{missing_opt_str}</p>
                    </div>
                </div>
            </div>

           <div class="row mb-4">
    <div class="col-12">
        <div class="score-circle">
            <span class="fs-3 fw-bold text-warning">{final_score}%</span>
            <small style="font-size: 0.65rem;" class="text-uppercase text-muted">Overall Score</small>
        </div>
    </div>
</div>
            <div class="p-3 rounded mb-4" style="background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.2);">
                <span class="text-warning"><strong>Recommendation:</strong></span>
                <span class="text-white-50">{suggestion}</span>
            </div>

            <div class="d-flex gap-3 justify-content-center">
                <a href="/student_dashboard" class="btn btn-premium">Go to Dashboard</a>
                <a href="/student_profile" class="btn btn-premium-outline" style="border-color: rgba(255,255,255,0.4); color: white;">View Profile</a>
            </div>
        </div>
    </body>
    </html>
    """

@app.route("/student_login")
def student_login_page():
    return render_template("student/login.html")

@app.route("/student_login_check", methods = ["POST"])
def student_login_check():
    email = request.form["email"]
    password = request.form["password"]
    remember = request.form.get("rememberMe")

    query = "SELECT * FROM students WHERE email = %s AND password = %s"
    cursor.execute(query, (email,password))
    student = cursor.fetchone()

    if student:
        session["student_id"] = student["student_id"]
        session["student_name"] = student["name"]
        session["must_change_password"] = student.get("must_change_password", 1)
        if remember:
            session.permanent = True
        return redirect("/student_dashboard")
    else :
        return render_template("student/login.html", error="Wrong password or invalid credentials.")

@app.route("/google_login_check", methods=["POST"])
def google_login_check():
    import base64
    credential = request.form.get("credential")
    remember = request.form.get("rememberMe")
    if not credential:
        return render_template("student/login.html", error="Google Sign-In failed.")
       
    try:
        parts = credential.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")
           
        payload = parts[1]
        payload += "=" * ((4 - len(payload) % 4) % 4)
        decoded_payload = base64.urlsafe_b64decode(payload).decode('utf-8')
        user_info = json.loads(decoded_payload)
       
        email = user_info.get("email")
        if not email:
            raise ValueError("Email not found in Google token")
           
        cursor.execute("SELECT * FROM students WHERE email = %s", (email,))
        student = cursor.fetchone()
       
        if student:
            session["student_id"] = student["student_id"]
            session["student_name"] = student["name"]
            if remember:
                session.permanent = True
            return redirect("/student_dashboard")
        else:
            return render_template("student/login.html", error=f"Email {email} is not registered. Please contact faculty.")
           
    except Exception as e:
        print("Google Auth Error:", e)
        return render_template("student/login.html", error="Google Sign-In verification failed.")
   
@app.route("/change_password", methods=["POST"])
def change_password():
    if "student_id" not in session:
        return redirect("/student_login")

    old_password = request.form.get("old_password", "").strip()
    new_password = request.form.get("new_password", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()

    if new_password != confirm_password:
        flash("New password and confirm password do not match", "danger")
        return redirect("/student_profile")

    cursor.execute(
        "SELECT * FROM students WHERE student_id=%s AND password=%s",
        (session["student_id"], old_password)
    )
    student = cursor.fetchone()

    if student:
        cursor.execute(
    "UPDATE students SET password=%s, must_change_password=0 WHERE student_id=%s",
    (new_password, session["student_id"])
        )
        db.commit()
        session["must_change_password"] = 0
        flash("Password changed successfully", "success")
    else:
        flash("Old password is incorrect", "danger")

    return redirect("/student_profile")

@app.route("/api/faculty_login", methods=["POST"])
def api_faculty_login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
   
    cursor.execute("SELECT * FROM faculty WHERE email = %s AND password = %s", (email, password))
    faculty = cursor.fetchone()
   
    if faculty:
        session["faculty_id"] = faculty["faculty_id"]
        session["faculty_name"] = faculty["name"]
        return jsonify({"success": True, "name": faculty["name"]})
    else:
        return jsonify({"success": False, "message": "Invalid email or password"})

@app.route("/clear_notifications", methods=["POST"])
def clear_notifications():
    if "student_id" in session:
        try:
            student_id = session["student_id"]
            cursor.execute("UPDATE notifications SET is_read = 1 WHERE student_id = %s", (student_id,))
            db.commit()
            return jsonify({"success": True})
        except Exception as e:
            print("Error clearing notifications:", e)
            return jsonify({"success": False, "error": str(e)})
    return jsonify({"success": False, "error": "Not logged in"})

@app.route("/student_dashboard")
def student_dashboard():
    ensure_connection()

    if "student_id" not in session:
        return redirect("/student_login")

    cursor.execute("SELECT * FROM students WHERE student_id = %s", (session["student_id"],))
    student = cursor.fetchone()

    try:
        cursor.execute("SELECT * FROM jobs ORDER BY id DESC")
    except Exception:
        cursor.execute("SELECT * FROM jobs ORDER BY job_id DESC")
    all_jobs = cursor.fetchall()

    upcoming_drives = []

    for job in all_jobs:
        job_tier_str = str(job.get("tier", "Tier 3")).lower()
        job_tier_num = 1 if "1" in job_tier_str else (2 if "2" in job_tier_str else 3)

        eligible_branches = [b.strip().lower() for b in job.get("branches", "").split(",")] if job.get("branches") else []
        student_branch = student["branch"].strip().lower() if student["branch"] else ""

        cgpa_ok = student["cgpa"] >= float(job.get("cgpa_cutoff") or 0)
        backlogs_ok = student["backlogs"] <= int(job.get("active_backlogs") or 0)
        branch_ok = student_branch in eligible_branches or not eligible_branches

        student_selected_tier = student.get("selected_tier")
        tier_ok = True

        if student_selected_tier is not None and student_selected_tier > 0:
            if student_selected_tier == 1 and job_tier_num in [2, 3]:
                tier_ok = False
            elif student_selected_tier == 2 and job_tier_num == 3:
                tier_ok = False

        is_eligible = cgpa_ok and backlogs_ok and branch_ok and tier_ok

        job_item = dict(job)
        job_item["is_eligible"] = is_eligible
        job_item["package_lpa"] = job.get("ctc") or ""
        job_item["deadline"] = str(job.get("deadline")) if job.get("deadline") else "Ongoing"

        upcoming_drives.append(job_item)

    eligible_count = sum(1 for job in upcoming_drives if job["is_eligible"])

    cursor.execute("SELECT COUNT(*) AS count FROM applications WHERE student_id = %s", (session["student_id"],))
    applied_count = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) AS count FROM applications WHERE student_id = %s AND status = 'Interview'", (session["student_id"],))
    interview_count = cursor.fetchone()["count"]

    resume_score = session.get("resume_score", 0)

    # Recent applications for the dashboard card
    cursor.execute("""
        SELECT a.applied_date, a.status, a.resume_path,
               j.company_name, j.role, j.ctc as package_lpa, j.tier, j.deadline
        FROM applications a
        JOIN jobs j ON a.job_id = j.job_id
        WHERE a.student_id = %s
        ORDER BY a.applied_date DESC
        LIMIT 5
    """, (session["student_id"],))
    recent_applications = cursor.fetchall()
    # Replace 'Not Selected' display for 'Rejected'
    for app in recent_applications:
        if app.get('status') == 'Rejected':
            app['status'] = 'Not Selected'

    cursor.execute("""
        SELECT * FROM notifications
        WHERE student_id = %s AND is_read = 0
        ORDER BY created_at DESC
        """, (session["student_id"],))

    notifications = cursor.fetchall()

    return render_template(
        "student/dashboard.html",
        name=student["name"],
        student=student,
        upcoming_drives=upcoming_drives,
        eligible_count=eligible_count,
        applied_count=applied_count,
        interview_count=interview_count,
        resume_score=resume_score,
        notifications=notifications,
        recent_applications=recent_applications
    )
@app.route("/student_profile")
def student_profile():
    ensure_connection()
    if "student_id" not in session:
        return redirect("/student_login")

    student_id = session["student_id"]

    query = "SELECT * FROM students WHERE student_id = %s"
    cursor.execute(query, (student_id,))
    student = cursor.fetchone()

    return render_template(
    "student/profile.html",
    student=student,
    must_change_password=session.get("must_change_password", 0)
)

@app.route("/update_profile", methods=["POST"])
def update_profile():
    if "student_id" not in session:
        return redirect("/student_login")
       
    student_id = session["student_id"]
   
    if "profile_photo" in request.files:
        photo = request.files["profile_photo"]
        if photo.filename != "":
            filename = secure_filename(photo.filename)
            upload_folder = os.path.join(app.root_path, "static", "uploads")
            os.makedirs(upload_folder, exist_ok=True)
            filepath = os.path.join(upload_folder, f"student_{student_id}_{filename}")
            photo.save(filepath)
           
            db_path = f"/static/uploads/student_{student_id}_{filename}"
            cursor.execute("UPDATE students SET profile_photo = %s WHERE student_id = %s", (db_path, student_id))
            db.commit()
           
    return redirect("/student_profile")

@app.route("/update_profile_details", methods=["POST"])
def update_profile_details():
    if "student_id" not in session:
        return redirect("/student_login")
       
    student_id = session["student_id"]
    roll_number = request.form.get("roll_number", "").strip()
    phone_number = request.form.get("phone_number", "").strip()
    aadhar = request.form.get("aadhar", "").strip()
    pan = request.form.get("pan", "").strip()
   
    try:
        from flask import flash
        flash("Profile edits are restricted to Faculty Master Sheet uploads.", "error")
    except Exception as e:
        pass
       
    return redirect("/student_profile")

@app.route("/update_skills", methods=["POST"])
def update_skills():
    ensure_connection()
    if "student_id" not in session:
        return redirect("/student_login")
       
    student_id = session["student_id"]
    skills = request.form.get("skills", "").strip()
   
    try:
        # Clean up skills string (remove extra spaces around commas)
        if skills:
            skills_list = [s.strip() for s in skills.split(',') if s.strip()]
            skills = ", ".join(skills_list)
           
        cursor.execute("UPDATE students SET skills = %s WHERE student_id = %s", (skills, student_id))
        db.commit()
        from flask import flash
        flash("Skills updated successfully!", "success")
    except Exception as e:
        db.rollback()
        from flask import flash
        flash("Failed to update skills.", "error")
       
    return redirect("/student_profile")

@app.route("/eligible_companies")
def eligible_companies():
    ensure_connection()
    if "student_id" not in session:
        return redirect("/student_login")
   
    student_id = session["student_id"]
    cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()
   
    try:
        cursor.execute("SELECT * FROM jobs ORDER BY id DESC")
    except Exception:
        cursor.execute("SELECT * FROM jobs ORDER BY job_id DESC")
    all_jobs = cursor.fetchall()
   
    # Check eligibility for each job
    jobs_list = []
    for job in all_jobs:
        job_tier_str = str(job.get('tier', 'Tier 3')).lower()
        job_tier_num = 1 if '1' in job_tier_str else (2 if '2' in job_tier_str else 3)

        eligible_branches = [b.strip().lower() for b in job.get('branches', '').split(',')] if job.get('branches') else []
        student_branch = student['branch'].strip().lower() if student['branch'] else ""
       
        cgpa_ok = student['cgpa'] >= float(job.get('cgpa_cutoff') or 0) if student['cgpa'] is not None else True
        backlogs_ok = student['backlogs'] <= int(job.get('active_backlogs') or 0) if student['backlogs'] is not None else True
        branch_ok = (student_branch in eligible_branches) or (not eligible_branches)
       
        # Tier check
        student_selected_tier = student.get('selected_tier')
        tier_ok = True
        if student_selected_tier is not None and student_selected_tier > 0:
            if student_selected_tier == 1 and job_tier_num in [2, 3]:
                tier_ok = False
            elif student_selected_tier == 2 and job_tier_num == 3:
                tier_ok = False

        reasons = []
        if not cgpa_ok:
            reasons.append(f"CGPA below requirement ({student['cgpa']} < {job.get('cgpa_cutoff')})")
        if not backlogs_ok:
            reasons.append(f"Backlogs exceed maximum allowed ({student['backlogs']} > {job.get('active_backlogs')})")
        if not branch_ok:
            reasons.append(f"Branch not eligible (Your branch: {student['branch'].upper()}, Eligible: {job.get('branches')})")
        if not tier_ok:
            reasons.append(f"Tier Policy restriction: Selected in Tier {student_selected_tier}, cannot apply for Tier {job_tier_num}")
           
        is_eligible = cgpa_ok and backlogs_ok and branch_ok and tier_ok
       
        # Check if already applied
        cursor.execute("SELECT * FROM applications WHERE student_id = %s AND job_id = %s", (student_id, job['job_id']))
        application = cursor.fetchone()
        applied = True if application else False
        status = application['status'] if application else None
       
        job_item = dict(job)
        job_item['is_eligible'] = is_eligible
        job_item['reasons'] = reasons
        job_item['applied'] = applied
        job_item['application_status'] = status
       
        job_item['package_lpa'] = job.get('ctc') or ''
        job_item['min_cgpa'] = job.get('cgpa_cutoff') or 0
        job_item['max_backlogs'] = job.get('active_backlogs') or 0
        job_item['eligible_branches'] = job.get('branches') or ''
        job_item['deadline'] = str(job.get('deadline')) if job.get('deadline') else 'Ongoing'

        jobs_list.append(job_item)
       
    return render_template("student/eligible_companies.html", jobs=jobs_list, student=student)

@app.route("/apply_job", methods=["POST"])
def apply_job():
    ensure_connection()
    if "student_id" not in session:
        return redirect("/student_login")
   
    student_id = session["student_id"]
    job_id = request.form.get("job_id")
    drive_link = request.form.get("drive_link")
   
    # Fetch student and job details to verify tier restrictions in backend
    cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()
    cursor.execute("SELECT * FROM jobs WHERE job_id = %s", (job_id,))
    job = cursor.fetchone()
   
    if not student or not job:
        return "Invalid request."
       
    # Check if deadline has passed
    from datetime import datetime
    if job.get('deadline'):
        deadline = job['deadline']
        if isinstance(deadline, str):
            try:
                deadline = datetime.strptime(deadline, "%Y-%m-%d %H:%M:%S")
            except Exception:
                try:
                    deadline = datetime.strptime(deadline, "%Y-%m-%dT%H:%M")
                except Exception:
                    pass
        if isinstance(deadline, datetime) and datetime.now() > deadline:
            return """
            <script>
                alert("Application deadline has passed for this job!");
                window.location.href = "/eligible_companies";
            </script>
            """
       
    # Tier calculation
    job_tier_str = str(job.get('tier', 'Tier 3')).lower()
    job_tier_num = 1 if '1' in job_tier_str else (2 if '2' in job_tier_str else 3)
       
    student_selected_tier = student.get('selected_tier')
    tier_ok = True
    if student_selected_tier is not None and student_selected_tier > 0:
        if student_selected_tier == 1 and job_tier_num in [2, 3]:
            tier_ok = False
        elif student_selected_tier == 2 and job_tier_num == 3:
            tier_ok = False
           
    if not tier_ok:
        return """
        <script>
            alert("Policy Violation: You are already selected in a Tier """ + str(student_selected_tier) + """ job. You cannot apply for Tier """ + str(job_tier_num) + """ roles.");
            window.location.href = "/eligible_companies";
        </script>
        """
   
    # Check if already applied
    cursor.execute("SELECT * FROM applications WHERE student_id = %s AND job_id = %s", (student_id, job_id))
    existing = cursor.fetchone()
    if existing:
        return """
        <script>
            alert("Already applied for this job!");
            window.location.href = "/eligible_companies";
        </script>
        """
   
    # Generate new application_id safely
    cursor.execute("SELECT COALESCE(MAX(application_id), 0) + 1 as next_id FROM applications")
    result = cursor.fetchone()
    next_id = result['next_id'] if result else 1
   
    # Extract dynamic extra details if present
    extra_data = {}
    aadhar = request.form.get("aadhar_number")
    pan = request.form.get("pan_number")
    other_info = request.form.get("other_info")
   
    if aadhar: extra_data["aadhar_number"] = aadhar
    if pan: extra_data["pan_number"] = pan
    if other_info: extra_data["other_info"] = other_info
   
    import json
    extra_details_json = json.dumps(extra_data) if extra_data else None
   
    query = """
        INSERT INTO applications (application_id, student_id, job_id, resume_path, status, applied_date, extra_details)
        VALUES (%s, %s, %s, %s, %s, CURDATE(), %s)
    """
    cursor.execute(query, (next_id, student_id, job_id, drive_link, "Pending", extra_details_json))
    db.commit()
   
    return """
    <script>
        alert("Application submitted successfully!");
        window.location.href = "/my_applications";
    </script>
    """

@app.route("/my_applications")
def my_applications():
    ensure_connection()
    if "student_id" not in session:
        return redirect("/student_login")
       
    student_id = session["student_id"]
    cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()
   
    query = """
        SELECT a.applied_date, a.status, a.resume_path,
               j.company_name, j.role, j.ctc as package_lpa, j.tier, j.deadline
        FROM applications a
        JOIN jobs j ON a.job_id = j.job_id
        WHERE a.student_id = %s
        ORDER BY a.applied_date DESC
    """
    cursor.execute(query, (student_id,))
    apps = cursor.fetchall()
    # Replace 'Rejected' with 'Not Selected'
    for app in apps:
        if app.get('status') == 'Rejected':
            app['status'] = 'Not Selected'
   
    return render_template("student/my_applications.html", applications=apps, student=student)

@app.route("/student_logout")
def student_logout():
    session.clear()
    return redirect("/student_login")

@app.route("/faculty_login")
def faculty_login_page():
    ensure_connection()
    try:
        cursor.execute("SELECT COUNT(*) AS c FROM students")
        total_students = cursor.fetchone()["c"]
    except Exception:
        total_students = 0
    try:
        cursor.execute("SELECT COUNT(*) AS c FROM jobs")
        active_jobs = cursor.fetchone()["c"]
    except Exception:
        active_jobs = 0
    return render_template("faculty/login.html", total_students=total_students, active_jobs=active_jobs)


@app.route("/faculty_login_check", methods=["POST"])
def faculty_login_check():
    ensure_connection()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()

    cursor.execute("SELECT * FROM faculty WHERE email = %s AND password = %s", (email, password))
    faculty = cursor.fetchone()

    if faculty:
        session["faculty_email"] = email
        session["faculty_name"] = faculty["name"]
        session.permanent = True
        return redirect("/faculty_dashboard")

    # Fallback for hardcoded Dr. Shankar
    if email == "drshankar@gmail.com" and password == "shankar123":
        session["faculty_email"] = email
        session["faculty_name"] = "Dr. Shankar"
        session.permanent = True
        return redirect("/faculty_dashboard")

    try:
        cursor.execute("SELECT COUNT(*) AS c FROM students")
        total_students = cursor.fetchone()["c"]
        cursor.execute("SELECT COUNT(*) AS c FROM jobs")
        active_jobs = cursor.fetchone()["c"]
    except Exception:
        total_students = active_jobs = 0
    return render_template("faculty/login.html", error="Invalid email or password.",
                           total_students=total_students, active_jobs=active_jobs)


def faculty_required():
    """Returns None if faculty is logged in, else a redirect response."""
    if "faculty_email" not in session:
        return redirect("/faculty_login")
    return None


@app.route("/faculty_dashboard")
def faculty_dashboard():
    ensure_connection()
    redir = faculty_required()
    if redir: return redir

    cursor.execute("SELECT COUNT(*) AS count FROM students")
    total_students = cursor.fetchone()["count"]
    cursor.execute("SELECT COUNT(*) AS count FROM jobs")
    active_jobs = cursor.fetchone()["count"]

    # Calculate average LPA
    cursor.execute("SELECT ctc FROM jobs WHERE ctc IS NOT NULL AND ctc != ''")
    ctc_rows = cursor.fetchall()
    total_lpa = 0
    count_lpa = 0
    for r in ctc_rows:
        import re
        m = re.search(r'([\d.]+)', str(r['ctc']))
        if m:
            total_lpa += float(m.group(1))
            count_lpa += 1
    avg_lpa = round(total_lpa / count_lpa, 1) if count_lpa > 0 else 0.0

    # Calculate placement rate
    cursor.execute("SELECT COUNT(DISTINCT student_id) as placed FROM applications WHERE status = 'Selected'")
    placed_students = cursor.fetchone()["placed"]
    placement_rate = round((placed_students / total_students * 100), 1) if total_students > 0 else 0.0

    # Check if master sheet file exists (pdf or xlsx)
    upload_dir = os.path.join(app.static_folder, "uploads")
    master_sheet_status = "Empty"
    if os.path.exists(os.path.join(upload_dir, "master_sheet.pdf")) or \
       os.path.exists(os.path.join(upload_dir, "master_sheet.xlsx")):
        master_sheet_status = "Uploaded"

    return render_template(
        "faculty/dashboard.html",
        name=session["faculty_name"],
        total_students=total_students,
        active_jobs=active_jobs,
        placement_rate=placement_rate,
        avg_lpa=avg_lpa,
        master_sheet_status=master_sheet_status
    )


@app.route("/faculty_logout")
def faculty_logout():
    session.pop("faculty_email", None)
    session.pop("faculty_name", None)
    return redirect("/faculty_login")


# ─── FACULTY: JOBS ───────────────────────────────────────────────────────────

@app.route("/faculty/jobs")
def faculty_jobs():
    ensure_connection()
    redir = faculty_required()
    if redir: return redir

    try:
        cursor.execute("SELECT * FROM jobs ORDER BY id DESC")
    except Exception:
        # Fallback if 'id' column doesn't exist in older schema
        cursor.execute("SELECT * FROM jobs ORDER BY job_id DESC")
    jobs = cursor.fetchall()
   
    for j in jobs:
        cursor.execute("SELECT COUNT(*) as c FROM applications WHERE job_id=%s", (j["job_id"],))
        j["applicant_count"] = cursor.fetchone()["c"]
   
    # Get custom columns dynamically
    cursor.execute("SHOW COLUMNS FROM jobs")
    all_columns = cursor.fetchall()
    custom_cols = [{"db_name": c["Field"], "label": c["Field"].replace("custom_", "").replace("_", " ").title()} for c in all_columns if c["Field"].startswith("custom_")]

    jobs_json = json.dumps([dict(j) for j in jobs], default=str)
    return render_template("faculty/jobs.html", jobs=jobs, jobs_json=jobs_json, custom_cols=custom_cols)


@app.route("/faculty/jobs/add", methods=["POST"])
def faculty_job_add():
    ensure_connection()
    redir = faculty_required()
    if redir: return redir

    job_id    = request.form.get("job_id", "").strip()
    company   = request.form.get("company_name", "").strip()
    role      = request.form.get("role", "").strip()
    ctc       = request.form.get("ctc", "").strip()
    location  = request.form.get("location", "").strip()
    bond      = request.form.get("bond", "None").strip()
    cgpa      = float(request.form.get("cgpa_cutoff", 0))
    act_bl    = int(request.form.get("active_backlogs", 0))
    bl_hist   = int(request.form.get("backlog_history", 0))
    branches_list = request.form.getlist("branches")

    custom_branch = request.form.get("custom_branch", "").strip()
    if custom_branch:
        branches_list.append(custom_branch)

    branches = ", ".join(branches_list)

    tier      = request.form.get("tier", "Tier 1")
    desc      = request.form.get("description", "").strip()
    req_aadhar = 1 if request.form.get("req_aadhar") else 0
    req_pan    = 1 if request.form.get("req_pan") else 0
    req_other  = request.form.get("req_other", "").strip()
    deadline   = request.form.get("deadline", "").strip() or None

    custom_fields = [
        k for k in request.form.keys()
        if k.startswith("custom_") and k != "custom_branch"
    ]
    custom_cols_str = ", ".join(custom_fields)
    custom_placeholders = ", ".join(["%s"] * len(custom_fields))
    custom_values = [request.form.get(k, "").strip() for k in custom_fields]

    pdf_path = None
    pdf_file = request.files.get("pdf_file")
    if pdf_file and pdf_file.filename:
        upload_dir = os.path.join(app.static_folder, "uploads", "job_pdfs")
        os.makedirs(upload_dir, exist_ok=True)
        fname = secure_filename(f"{job_id}_{pdf_file.filename}")
        pdf_file.save(os.path.join(upload_dir, fname))
        pdf_path = f"/static/uploads/job_pdfs/{fname}"

    try:
        col_sql = f", {custom_cols_str}" if custom_cols_str else ""
        val_sql = f", {custom_placeholders}" if custom_placeholders else ""
        cursor.execute(f"""
            INSERT INTO jobs (job_id, company_name, role, ctc, location, bond,
                cgpa_cutoff, active_backlogs, backlog_history, branches, tier,
                description, req_aadhar, req_pan, req_other, pdf_path, deadline{col_sql})
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s{val_sql})
        """, [job_id, company, role, ctc, location, bond,
               cgpa, act_bl, bl_hist, branches, tier,
               desc, req_aadhar, req_pan, req_other, pdf_path, deadline] + custom_values)
        db.commit()
        # Notify all students about the new job
        notify_students_new_job(company, role)
        from flask import flash
        flash(f"Job opening for {company} added successfully!", "success")
    except Exception as e:
        db.rollback()
        from flask import flash
        flash(f"Error adding job: {str(e)}", "error")

    return redirect("/faculty/jobs")


@app.route("/faculty/jobs/edit", methods=["POST"])
def faculty_job_edit():
    ensure_connection()
    redir = faculty_required()
    if redir: return redir

    db_job_id = request.form.get("job_id_edit", "").strip() or request.form.get("job_id", "").strip()
    company   = request.form.get("company_name", "").strip()
    role      = request.form.get("role", "").strip()
    ctc       = request.form.get("ctc", "").strip()
    location  = request.form.get("location", "").strip()
    bond      = request.form.get("bond", "None").strip()
    cgpa      = float(request.form.get("cgpa_cutoff", 0))
    act_bl    = int(request.form.get("active_backlogs", 0))
    bl_hist   = int(request.form.get("backlog_history", 0))
    branches_list = request.form.getlist("branches")

    custom_branch = request.form.get("custom_branch", "").strip()
    if custom_branch:
        branches_list.append(custom_branch)

    branches = ", ".join(branches_list)
   
    tier      = request.form.get("tier", "Tier 1")
    desc      = request.form.get("description", "").strip()
    req_aadhar = 1 if request.form.get("req_aadhar") else 0
    req_pan    = 1 if request.form.get("req_pan") else 0
    req_other  = request.form.get("req_other", "").strip()
    deadline   = request.form.get("deadline", "").strip() or None

    custom_fields = [
    k for k in request.form.keys()
    if k.startswith("custom_") and k != "custom_branch"
]
    custom_set_sql = "".join([f", {k}=%s" for k in custom_fields])
    custom_values = [request.form.get(k, "").strip() for k in custom_fields]

    # Check if a new PDF was uploaded
    pdf_file = request.files.get("pdf_file")
    pdf_update_sql = ""
    pdf_args = []
    if pdf_file and pdf_file.filename:
        upload_dir = os.path.join(app.static_folder, "uploads", "job_pdfs")
        os.makedirs(upload_dir, exist_ok=True)
        fname = secure_filename(f"job_{db_job_id}_{pdf_file.filename}")
        pdf_file.save(os.path.join(upload_dir, fname))
        pdf_update_sql = ", pdf_path=%s"
        pdf_args = [f"/static/uploads/job_pdfs/{fname}"]

    try:
        cursor.execute(f"""
            UPDATE jobs SET company_name=%s, role=%s, ctc=%s, location=%s, bond=%s,
                cgpa_cutoff=%s, active_backlogs=%s, backlog_history=%s, branches=%s,
                tier=%s, description=%s, req_aadhar=%s, req_pan=%s, req_other=%s, deadline=%s
                {pdf_update_sql}
                {custom_set_sql}
            WHERE job_id = %s
        """, [company, role, ctc, location, bond,
               cgpa, act_bl, bl_hist, branches, tier,
               desc, req_aadhar, req_pan, req_other, deadline] + pdf_args + custom_values + [db_job_id])
       
        db.commit()

        from flask import flash
        flash(f"Job for {company} updated successfully!", "success")
    except Exception as e:
        db.rollback()
        from flask import flash
        flash(f"Error updating job: {str(e)}", "error")

    return redirect("/faculty/jobs")


@app.route("/faculty/jobs/add_column", methods=["POST"])
def faculty_job_add_column():
    ensure_connection()
    redir = faculty_required()
    if redir: return redir
   
    name = request.form.get("name", "").strip()
    col_type = request.form.get("type", "").strip()
   
    if not name:
        from flask import flash
        flash("Column name cannot be empty.", "error")
        return redirect("/faculty/jobs")
       
    import re
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower())
    col_name = f"custom_{sanitized}"
   
    sql_type = "VARCHAR(255)"
    if col_type == "number":
        sql_type = "DECIMAL(10,2)"
    elif col_type == "boolean":
        sql_type = "TINYINT(1)"
       
    try:
        cursor.execute(f"ALTER TABLE jobs ADD COLUMN {col_name} {sql_type}")
        db.commit()
        from flask import flash
        flash(f"Custom column '{name}' added successfully!", "success")
    except Exception as e:
        db.rollback()
        from flask import flash
        flash(f"Error adding column: {str(e)}", "error")
       
    return redirect("/faculty/jobs")

@app.route("/faculty/jobs/delete_all", methods=["POST"])
def faculty_jobs_delete_all():
    ensure_connection()
    redir = faculty_required()
    if redir:
        return redir

    try:
        cursor.execute("DELETE FROM applications")
        cursor.execute("DELETE FROM jobs")
        db.commit()
        flash("All job openings deleted successfully!", "success")
    except Exception as e:
        db.rollback()
        flash(f"Error deleting job openings: {str(e)}", "error")

    return redirect("/faculty/jobs")


@app.route("/faculty/jobs/delete/<string:job_db_id>", methods=["POST"])
def faculty_job_delete(job_db_id):
    ensure_connection()
    redir = faculty_required()
    if redir: return jsonify({"success": False, "error": "Not logged in"})
    try:
        cursor.execute("DELETE FROM jobs WHERE job_id=%s", (job_db_id,))
        db.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)})


@app.route("/faculty/jobs/delete_column/<string:col_name>", methods=["POST"])
def faculty_job_delete_column(col_name):
    ensure_connection()
    redir = faculty_required()
    if redir: return jsonify({"success": False, "error": "Not logged in"})
    try:
        import re
        if not re.match(r'^custom_[a-zA-Z0-9_]+$', col_name):
            raise Exception("Invalid column name")
        cursor.execute(f"ALTER TABLE jobs DROP COLUMN {col_name}")
        db.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)})


@app.route("/faculty/jobs/applicants/<string:job_db_id>")
def faculty_job_applicants(job_db_id):
    ensure_connection()
    redir = faculty_required()
    if redir: return jsonify({"applicants": []})

    cursor.execute("""
        SELECT a.*, s.name, s.branch, s.student_id
        FROM applications a
        JOIN students s ON a.student_id = s.student_id
        WHERE a.job_id = %s
    """, (job_db_id,))
    apps = cursor.fetchall()
    return jsonify({"applicants": [dict(a) for a in apps]})


@app.route("/faculty/job_pdf/<string:job_db_id>")
def faculty_job_pdf(job_db_id):
    ensure_connection()
    redir = faculty_required()
    if redir: return redir

    cursor.execute("SELECT pdf_path FROM jobs WHERE job_id=%s", (job_db_id,))
    job = cursor.fetchone()
    if not job or not job["pdf_path"]:
        from flask import flash
        flash("No PDF attached to this job.", "error")
        return redirect("/faculty/jobs")
   
    # Strip the leading '/static/' to get the true relative path in the static folder
    pdf_path = job["pdf_path"]
    if pdf_path.startswith("/static/"):
        pdf_path = pdf_path[8:]
    from flask import send_from_directory
    return send_from_directory(app.static_folder, pdf_path)


@app.route("/faculty/applications/update_status", methods=["POST"])
def faculty_applications_update_status():
    ensure_connection()
    redir = faculty_required()
    if redir: return jsonify({"success": False, "error": "Faculty authorization required"})

    data = request.get_json() or {}
    app_id = data.get("application_id")
    status = data.get("status")
    # Normalize 'Not Selected' to 'Not Selected' (was 'Rejected')
    if status == 'Rejected':
        status = 'Not Selected'

    if not app_id or not status:
        return jsonify({"success": False, "error": "Missing application_id or status"})

    try:
        # Fetch current details before updating
        cursor.execute("SELECT student_id, job_id, status FROM applications WHERE application_id = %s", (app_id,))
        app_record = cursor.fetchone()
        if not app_record:
            return jsonify({"success": False, "error": "Application not found"})

        student_id = app_record["student_id"]
        job_db_id = app_record["job_id"]
        old_status = app_record["status"]

        # Update applications table
        cursor.execute("UPDATE applications SET status = %s WHERE application_id = %s", (status, app_id))

        # Check the job company and role/tier
        cursor.execute("SELECT company_name, role, tier FROM jobs WHERE job_id = %s", (job_db_id,))
        job_details = cursor.fetchone()
        company_name = job_details["company_name"] if job_details else "Company"
        role_name = job_details["role"] if job_details else "Role"
        job_tier_str = job_details["tier"] if job_details else "Tier 3"
        job_tier_num = 1 if '1' in job_tier_str else (2 if '2' in job_tier_str else 3)

        # Notify student if status changed
        if old_status != status:
            message = f"Your application status for {company_name} - {role_name} has been updated to {status}."
            if status == "Selected":
                message = f"Congratulations! You have been Selected by {company_name} for the {role_name} role (Tier {job_tier_str})!"
           
            cursor.execute("INSERT INTO notifications (student_id, message, link) VALUES (%s, %s, %s)",
                           (student_id, message, "/my_applications"))

        # Re-evaluate the student selected_tier:
        # Find the highest tier level among all 'Selected' applications for this student
        cursor.execute("""
            SELECT j.tier
            FROM applications a
            JOIN jobs j ON a.job_id = j.job_id
            WHERE a.student_id = %s AND a.status = 'Selected'
        """, (student_id,))
        selected_apps = cursor.fetchall()
       
        if selected_apps:
            # Calculate highest tier selected (lower tier number is better, i.e., Tier 1 is better than Tier 2)
            highest_tier_num = 3
            for sa in selected_apps:
                t_str = sa["tier"] or "Tier 3"
                t_num = 1 if '1' in t_str else (2 if '2' in t_str else 3)
                if t_num < highest_tier_num:
                    highest_tier_num = t_num
            cursor.execute("UPDATE students SET selected_tier = %s WHERE student_id = %s", (highest_tier_num, student_id))
        else:
            # Clear selected tier
            cursor.execute("UPDATE students SET selected_tier = NULL WHERE student_id = %s", (student_id,))

        db.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)})


@app.route("/faculty/selected_students")
def faculty_selected_students():
    ensure_connection()
    redir = faculty_required()
    if redir: return redir

    # Query all students who are selected for any job
    query = """
        SELECT s.student_id, s.name, s.email, s.branch, s.roll_number, s.phone_number,
               a.status, j.company_name, j.tier, j.job_id
        FROM students s
        JOIN applications a ON s.student_id = a.student_id
        JOIN jobs j ON a.job_id = j.job_id
        WHERE a.status = 'Selected'
        ORDER BY s.student_id ASC
    """
    cursor.execute(query)
    placed = cursor.fetchall()

    return render_template("faculty/selected_students.html", placed_students=placed)


@app.route("/faculty/applied_students")
def faculty_applied_students():
    ensure_connection()
    redir = faculty_required()
    if redir: return redir

    try:
        cursor.execute("SELECT * FROM jobs ORDER BY id DESC")
    except Exception:
        cursor.execute("SELECT * FROM jobs ORDER BY job_id DESC")
    jobs = cursor.fetchall()

    # Format deadlines and query applicants count
    jobs_list = []
    for job in jobs:
        j = dict(job)
        # Check if deadline passed
        from datetime import datetime
        is_passed = False
        if j.get('deadline'):
            deadline = j['deadline']
            if isinstance(deadline, str):
                try:
                    deadline = datetime.strptime(deadline, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    try:
                        deadline = datetime.strptime(deadline, "%Y-%m-%dT%H:%M")
                    except Exception:
                        pass
            if isinstance(deadline, datetime) and datetime.now() > deadline:
                is_passed = True
       
        j['is_deadline_passed'] = is_passed
        j['deadline_str'] = str(j.get('deadline')) if j.get('deadline') else 'Ongoing'

        # Query applicants details
        cursor.execute("""
            SELECT s.student_id, s.name, s.branch, s.roll_number, s.phone_number, s.email, s.aadhar, s.pan, a.resume_path, a.applied_date, a.extra_details
            FROM applications a
            JOIN students s ON a.student_id = s.student_id
            WHERE a.job_id = %s
            ORDER BY a.applied_date DESC
        """, (j['job_id'],))
        applicants = cursor.fetchall()
        for applicant in applicants:
            if applicant.get('extra_details'):
                try:
                    applicant['extra_dict'] = json.loads(applicant['extra_details'])
                except:
                    applicant['extra_dict'] = {}
            else:
                applicant['extra_dict'] = {}
               
        j['applicants'] = applicants
        jobs_list.append(j)

    return render_template("faculty/applied_students.html", jobs=jobs_list)


@app.route("/faculty/job_results")
def faculty_job_results():
    ensure_connection()
    redir = faculty_required()
    if redir: return redir

    try:
        cursor.execute("SELECT * FROM jobs ORDER BY id DESC")
    except Exception:
        cursor.execute("SELECT * FROM jobs ORDER BY job_id DESC")
    jobs = cursor.fetchall()
    
    for j in jobs:
        cursor.execute("SELECT COUNT(*) as c FROM applications WHERE job_id=%s", (j["job_id"],))
        j["applicant_count"] = cursor.fetchone()["c"]

    return render_template("faculty/job_results.html", jobs=jobs)


# ─── FACULTY: RECRUITMENT PROCESS TRACKER ─────────────────────────────────────

@app.route("/faculty/recruitment_process")
def faculty_recruitment_process():
    ensure_connection()
    redir = faculty_required()
    if redir: return redir

    try:
        cursor.execute("SELECT * FROM jobs ORDER BY id DESC")
    except Exception:
        cursor.execute("SELECT * FROM jobs ORDER BY job_id DESC")
    jobs = cursor.fetchall()

    jobs_data = []
    for j in jobs:
        jdict = dict(j)
        # Get number of rounds configured for this job
        cursor.execute("SELECT num_rounds FROM recruitment_rounds WHERE job_id=%s", (j["job_id"],))
        rr = cursor.fetchone()
        jdict["num_rounds"] = rr["num_rounds"] if rr else 1

        # Get all applicants for this job
        cursor.execute("""
            SELECT s.student_id, s.name, s.branch, s.roll_number, s.email, s.phone_number
            FROM applications a
            JOIN students s ON a.student_id = s.student_id
            WHERE a.job_id = %s
            ORDER BY s.name ASC
        """, (j["job_id"],))
        students = cursor.fetchall()

        # Get round results for all students in this job (include drive_link)
        cursor.execute("""
            SELECT student_id, round_number, result, drive_link
            FROM round_results
            WHERE job_id=%s
        """, (j["job_id"],))
        rr_rows = cursor.fetchall()
        # Build dicts: {student_id: {round_number: result}} and {student_id: {round_number: drive_link}}
        round_map = {}
        link_map  = {}
        for rrow in rr_rows:
            sid = rrow["student_id"]
            rnd = rrow["round_number"]
            round_map.setdefault(sid, {})[rnd] = rrow["result"]
            link_map.setdefault(sid,  {})[rnd] = rrow["drive_link"] or ""

        # Include ALL students (even not-selected) so faculty can see full picture
        students_list = []
        for s in students:
            sid = s["student_id"]
            s_dict = dict(s)
            s_dict["rounds"] = {}
            s_dict["links"]  = {}
            for rnd in range(1, jdict["num_rounds"] + 1):
                s_dict["rounds"][rnd] = round_map.get(sid, {}).get(rnd, "Pending")
                s_dict["links"][rnd]  = link_map.get(sid,  {}).get(rnd, "")
            students_list.append(s_dict)

        jdict["students"] = students_list
        jdict["applicant_count"] = len(list(students))
        jobs_data.append(jdict)

    return render_template("faculty/recruitment_process.html", jobs=jobs_data)


@app.route("/faculty/recruitment_process/set_rounds", methods=["POST"])
def set_recruitment_rounds():
    ensure_connection()
    redir = faculty_required()
    if redir: return jsonify({"success": False, "error": "Not logged in"})
    data = request.get_json() or {}
    job_id = data.get("job_id")
    num_rounds = int(data.get("num_rounds", 1))
    try:
        cursor.execute("""
            INSERT INTO recruitment_rounds (job_id, num_rounds)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE num_rounds = %s
        """, (job_id, num_rounds, num_rounds))
        db.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)})


@app.route("/faculty/recruitment_process/set_result", methods=["POST"])
def set_round_result():
    ensure_connection()
    redir = faculty_required()
    if redir: return jsonify({"success": False, "error": "Not logged in"})
    data = request.get_json() or {}
    job_id = data.get("job_id")
    student_id = data.get("student_id")
    round_number = int(data.get("round_number", 1))
    result = data.get("result", "Pending")  # 'Selected', 'Not Selected', 'Pending'
    try:
        cursor.execute("""
            INSERT INTO round_results (job_id, student_id, round_number, result)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE result = %s
        """, (job_id, student_id, round_number, result, result))
        db.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)})


@app.route("/faculty/recruitment_process/export_excel/<string:job_id>")
def export_recruitment_excel(job_id):
    ensure_connection()
    redir = faculty_required()
    if redir: return redir

    round_num = request.args.get('round', type=int)

    cursor.execute("SELECT company_name, role FROM jobs WHERE job_id = %s", (job_id,))
    job = cursor.fetchone()
    if not job:
        return "Job not found", 404

    company_name = job["company_name"]
    role_name = job["role"]

    cursor.execute("SELECT num_rounds FROM recruitment_rounds WHERE job_id=%s", (job_id,))
    rr = cursor.fetchone()
    num_rounds = rr["num_rounds"] if rr else 1

    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
    import io

    amber_fill = PatternFill(start_color="F59E0B", end_color="F59E0B", fill_type="solid")
    blue_fill  = PatternFill(start_color="3B82F6", end_color="3B82F6", fill_type="solid")
    green_fill = PatternFill(start_color="10B981", end_color="10B981", fill_type="solid")
    red_fill   = PatternFill(start_color="EF4444", end_color="EF4444", fill_type="solid")
    white_font   = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font   = Font(name="Calibri", size=14, bold=True, color="78350F")
    regular_font = Font(name="Calibri", size=11)
    instr_font   = Font(name="Calibri", size=10, italic=True, color="6B7280")
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left_align   = Alignment(horizontal="left",   vertical="center")
    thin_border  = Border(
        left=Side(style='thin', color='E5E7EB'), right=Side(style='thin', color='E5E7EB'),
        top=Side(style='thin', color='E5E7EB'),  bottom=Side(style='thin', color='E5E7EB')
    )

    # Fetch all applicants
    cursor.execute("""
        SELECT s.student_id, s.name, s.branch, s.roll_number, s.email, s.phone_number
        FROM applications a
        JOIN students s ON a.student_id = s.student_id
        WHERE a.job_id = %s
        ORDER BY s.name ASC
    """, (job_id,))
    all_students = cursor.fetchall()

    # Fetch existing round results (including drive_link)
    cursor.execute("SELECT student_id, round_number, result, drive_link FROM round_results WHERE job_id=%s", (job_id,))
    rr_rows = cursor.fetchall()
    round_map = {}
    link_map  = {}
    for rrow in rr_rows:
        sid = rrow["student_id"]
        rnd = rrow["round_number"]
        round_map.setdefault(sid, {})[rnd] = rrow["result"]
        link_map.setdefault(sid,  {})[rnd] = rrow["drive_link"] or ""

    # ── PER-ROUND EXPORT ─────────────────────────────────────────────────────────
    if round_num:
        # Filter eligible students: selected in all prior rounds (or all for round 1)
        eligible = []
        for s in all_students:
            sid = s["student_id"]
            ok = True
            for prev in range(1, round_num):
                if round_map.get(sid, {}).get(prev, "Pending") == "Not Selected":
                    ok = False
                    break
            if ok:
                eligible.append(s)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Round {round_num}"

        # Title
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=9)
        ws.cell(1, 1).value = f"Round {round_num} — {company_name} ({role_name})"
        ws.cell(1, 1).font = title_font
        ws.cell(1, 1).alignment = left_align
        ws.row_dimensions[1].height = 30

        # Instructions
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=9)
        ws.cell(2, 1).value = (
            f"INSTRUCTIONS: In column 'Round {round_num}', enter {round_num} if student is selected, "
            f"0 if not selected. Paste the Google Drive / interview link in 'Drive Link' column for selected students."
        )
        ws.cell(2, 1).font = instr_font
        ws.cell(2, 1).alignment = left_align
        ws.row_dimensions[2].height = 22

        # Headers (row 3)
        hdrs = [
            "S.No", "Student ID", "Roll No", "Student Name", "Branch", "Email", "Phone",
            f"Round {round_num}  (enter {round_num}=selected / 0=not selected)",
            "Drive Link  (paste here for selected students)"
        ]
        for ci, h in enumerate(hdrs, 1):
            c = ws.cell(3, ci, h)
            c.font  = white_font
            c.fill  = amber_fill if ci <= 7 else blue_fill
            c.alignment = center_align
            c.border = thin_border
        ws.row_dimensions[3].height = 36

        # Data rows
        for ri, s in enumerate(eligible, 1):
            row_num = ri + 3
            sid = s["student_id"]
            existing_res  = round_map.get(sid, {}).get(round_num, "")
            existing_link = link_map.get(sid, {}).get(round_num, "")
            if existing_res == "Selected":
                rval = round_num
            elif existing_res == "Not Selected":
                rval = 0
            else:
                rval = ""
            vals = [ri, sid, s["roll_number"] or "—", s["name"], s["branch"],
                    s["email"], s["phone_number"] or "—", rval, existing_link]
            for ci, v in enumerate(vals, 1):
                c = ws.cell(row_num, ci, v)
                c.font  = regular_font
                c.alignment = left_align if ci in (4, 6, 9) else center_align
                c.border = thin_border

        # Column widths
        for ci, w in enumerate([6, 12, 15, 28, 16, 32, 14, 44, 52], 1):
            ws.column_dimensions[get_column_letter(ci)].width = w

        out = io.BytesIO()
        wb.save(out)
        out.seek(0)
        from flask import send_file
        clean = "".join([ch for ch in company_name if ch.isalnum() or ch in (' ', '_')]).strip()
        return send_file(out, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                         as_attachment=True,
                         download_name=f"Round{round_num}_{clean}_{job_id}.xlsx")

    # ── FULL SUMMARY EXPORT (no round param) ─────────────────────────────────────
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Recruitment Process"

    # num_cols = 6 base + (Round + Drive Link) * num_rounds
    num_cols = 6 + num_rounds * 2

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=num_cols)
    ws.cell(1, 1).value = f"Recruitment Process — {company_name} ({role_name})"
    ws.cell(1, 1).font  = title_font
    ws.cell(1, 1).alignment = left_align
    ws.row_dimensions[1].height = 30

    base_headers = ["S.No", "Roll Number", "Student Name", "Branch", "Email", "Phone"]
    round_headers = []
    for i in range(1, num_rounds + 1):
        round_headers.append(f"Round {i}")
        round_headers.append(f"Drive Link {i}")
    all_headers = base_headers + round_headers

    for ci, h in enumerate(all_headers, 1):
        c = ws.cell(3, ci, h)
        c.font  = white_font
        c.fill  = amber_fill
        c.alignment = center_align
        c.border = thin_border
    ws.row_dimensions[3].height = 24

    for ri, s in enumerate(all_students, 1):
        row_num = ri + 3
        sid = s["student_id"]
        vals = [ri, s["roll_number"] or "—", s["name"], s["branch"], s["email"], s["phone_number"] or "—"]
        for ci, v in enumerate(vals, 1):
            c = ws.cell(row_num, ci, v)
            c.font  = regular_font
            c.alignment = left_align if ci in (3, 5) else center_align
            c.border = thin_border
        for rnd in range(1, num_rounds + 1):
            res  = round_map.get(sid, {}).get(rnd, "Pending")
            link = link_map.get(sid, {}).get(rnd, "")
            ci_res  = 6 + (rnd - 1) * 2 + 1
            ci_link = ci_res + 1
            c = ws.cell(row_num, ci_res, res)
            if res == "Selected":
                c.font  = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
                c.fill  = green_fill
            elif res == "Not Selected":
                c.font  = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
                c.fill  = red_fill
            else:
                c.font  = regular_font
                c.fill  = PatternFill()
            c.alignment = center_align
            c.border = thin_border
            cl = ws.cell(row_num, ci_link, link or "")
            cl.font  = regular_font
            cl.alignment = left_align
            cl.border = thin_border

    for col in ws.columns:
        max_len = max((len(str(c.value or '')) for c in col if c.row >= 3), default=10)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 4, 50)

    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    from flask import send_file
    clean = "".join([ch for ch in company_name if ch.isalnum() or ch in (' ', '_')]).strip()
    return send_file(out, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     as_attachment=True,
                     download_name=f"RecruitmentProcess_{clean}_{job_id}.xlsx")


@app.route("/faculty/recruitment_process/upload_excel/<string:job_id>/<int:round_num>", methods=["POST"])
def upload_recruitment_excel(job_id, round_num):
    """Parse an uploaded Round-N Excel and update round_results + auto-finalise application status."""
    ensure_connection()
    redir = faculty_required()
    if redir: return jsonify({"success": False, "error": "Not logged in"})

    if 'excel_file' not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"})

    file = request.files['excel_file']
    if not file.filename.lower().endswith('.xlsx'):
        return jsonify({"success": False, "error": "Please upload a .xlsx file"})

    import openpyxl, io as _io

    try:
        content = file.read()
        wb = openpyxl.load_workbook(_io.BytesIO(content), data_only=True)
        ws = wb.active

        # Locate header row (row 3) and map column names → 1-based column index
        headers = {}
        for cell in ws[3]:
            if cell.value is not None:
                key = str(cell.value).strip().lower()
                headers[key] = cell.column

        # Resolve Student ID, Round N, Drive Link columns
        student_id_col = drive_link_col = round_col = None
        for key, col in headers.items():
            if 'student id' in key:
                student_id_col = col
            if f'round {round_num}' in key:
                round_col = col
            if 'drive link' in key:
                drive_link_col = col

        if not student_id_col:
            return jsonify({"success": False, "error": "Could not find 'Student ID' column in the Excel file."})
        if not round_col:
            return jsonify({"success": False, "error": f"Could not find 'Round {round_num}' column in the Excel file."})

        updated = 0
        errors  = []

        for row in ws.iter_rows(min_row=4, values_only=True):
            raw_sid = row[student_id_col - 1]
            if raw_sid is None:
                continue
            try:
                student_id   = int(float(str(raw_sid)))
                round_value  = row[round_col - 1]
                drive_link   = row[drive_link_col - 1] if drive_link_col else None

                if round_value is None or str(round_value).strip() == "":
                    continue  # faculty left blank — skip

                rv = float(str(round_value).strip())
                if rv == 0:
                    result = "Not Selected"
                    drive_link = None          # clear link for eliminated students
                elif rv == round_num:
                    result = "Selected"
                else:
                    continue  # unexpected value — skip

                dl = str(drive_link).strip() if drive_link else None
                if dl in (None, "", "None"):
                    dl = None

                cursor.execute("""
                    INSERT INTO round_results (job_id, student_id, round_number, result, drive_link)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE result = VALUES(result), drive_link = VALUES(drive_link)
                """, (job_id, student_id, round_num, result, dl))
                updated += 1
            except Exception as row_err:
                errors.append(str(row_err))

        # ── AUTO-FINALISE WHEN LAST ROUND IS UPLOADED ────────────────────────────
        cursor.execute("SELECT num_rounds FROM recruitment_rounds WHERE job_id=%s", (job_id,))
        rr = cursor.fetchone()
        num_rounds = rr["num_rounds"] if rr else 1

        if round_num == num_rounds:
            cursor.execute("""
                SELECT s.student_id
                FROM applications a
                JOIN students s ON a.student_id = s.student_id
                WHERE a.job_id = %s
            """, (job_id,))
            all_students = cursor.fetchall()

            cursor.execute("SELECT student_id, round_number, result FROM round_results WHERE job_id=%s", (job_id,))
            all_results = cursor.fetchall()
            res_map = {}
            for r in all_results:
                res_map.setdefault(r["student_id"], {})[r["round_number"]] = r["result"]

            cursor.execute("SELECT tier FROM jobs WHERE job_id=%s", (job_id,))
            job_det   = cursor.fetchone()
            tier_str  = job_det["tier"] if job_det else "Tier 3"
            tier_num  = 1 if '1' in tier_str else (2 if '2' in tier_str else 3)

            for s in all_students:
                sid = s["student_id"]
                sres = res_map.get(sid, {})
                all_sel = all(sres.get(r, "Pending") == "Selected" for r in range(1, num_rounds + 1))
                any_not = any(sres.get(r, "Pending") == "Not Selected" for r in range(1, num_rounds + 1))

                if all_sel:
                    cursor.execute(
                        "UPDATE applications SET status='Selected' WHERE student_id=%s AND job_id=%s",
                        (sid, job_id))
                    cursor.execute(
                        "UPDATE students SET selected_tier=%s WHERE student_id=%s",
                        (tier_num, sid))
                    # Notify student
                    msg = f"Congratulations! You have been Selected for {job_id}. All {num_rounds} rounds cleared!"
                    cursor.execute(
                        "INSERT INTO notifications (student_id, message, link) VALUES (%s, %s, %s)",
                        (sid, msg, "/my_applications"))
                elif any_not:
                    cursor.execute(
                        "UPDATE applications SET status='Not Selected' WHERE student_id=%s AND job_id=%s",
                        (sid, job_id))

        db.commit()
        return jsonify({"success": True, "updated": updated, "errors": errors,
                        "finalised": (round_num == num_rounds)})

    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)})


@app.route("/faculty/job_results/<string:job_id>")
def faculty_job_results_api(job_id):
    ensure_connection()
    if "faculty_email" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    # Get selected
    cursor.execute("""
        SELECT s.student_id, s.name, s.email, s.branch, s.roll_number, s.phone_number
        FROM students s
        JOIN applications a ON s.student_id = a.student_id
        WHERE a.job_id = %s AND a.status = 'Selected'
        ORDER BY s.name ASC
    """, (job_id,))
    selected = cursor.fetchall()

    # Get not selected (was rejected)
    cursor.execute("""
        SELECT s.student_id, s.name, s.email, s.branch, s.roll_number, s.phone_number
        FROM students s
        JOIN applications a ON s.student_id = a.student_id
        WHERE a.job_id = %s AND (a.status = 'Rejected' OR a.status = 'Not Selected')
        ORDER BY s.name ASC
    """, (job_id,))
    not_selected = cursor.fetchall()

    return jsonify({"selected": selected, "not_selected": not_selected})

@app.route("/faculty/not_selected_students")
def faculty_not_selected_students():
    ensure_connection()
    redir = faculty_required()
    if redir: return redir

    # Query all students who are not selected for any job
    query = """
        SELECT s.student_id, s.name, s.email, s.branch, s.roll_number, s.phone_number,
               a.status, j.company_name, j.role, j.job_id
        FROM students s
        JOIN applications a ON s.student_id = a.student_id
        JOIN jobs j ON a.job_id = j.job_id
        WHERE a.status = 'Rejected' OR a.status = 'Not Selected'
        ORDER BY s.name ASC
    """
    cursor.execute(query)
    not_selected = cursor.fetchall()

    return render_template("faculty/rejected_students.html", rejected_students=not_selected)

# Keep old route as alias
@app.route("/faculty/rejected_students")
def faculty_rejected_students():
    return faculty_not_selected_students()


@app.route("/faculty/download_applied_excel/<string:job_id>")
def faculty_download_applied_excel(job_id):
    ensure_connection()
    redir = faculty_required()
    if redir: return redir

    # Fetch job company & role
    cursor.execute("SELECT company_name, role FROM jobs WHERE job_id = %s", (job_id,))
    job = cursor.fetchone()
    if not job:
        return "Job not found", 404

    company_name = job["company_name"]
    role_name = job["role"]

    # Fetch applied students
    cursor.execute("""
        SELECT s.student_id, s.name, s.branch, s.roll_number, s.phone_number, s.email, s.aadhar, s.pan, a.resume_path
        FROM applications a
        JOIN students s ON a.student_id = s.student_id
        WHERE a.job_id = %s
        ORDER BY s.student_id ASC
    """, (job_id,))
    applicants = cursor.fetchall()

    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
    import io

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Applied Students"

    # Set grid lines visible
    ws.views.sheetView[0].showGridLines = True

    # Styling colors
    amber_fill = PatternFill(start_color="F59E0B", end_color="F59E0B", fill_type="solid")
    white_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Calibri", size=14, bold=True, color="78350F")
    regular_font = Font(name="Calibri", size=11, bold=False)
    bold_font = Font(name="Calibri", size=11, bold=True)
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")

    thin_border = Border(
        left=Side(style='thin', color='E5E7EB'),
        right=Side(style='thin', color='E5E7EB'),
        top=Side(style='thin', color='E5E7EB'),
        bottom=Side(style='thin', color='E5E7EB')
    )

    # Title row
    ws.merge_cells("A1:I1")
    ws["A1"] = f"Applied Students - {company_name} ({role_name})"
    ws["A1"].font = title_font
    ws["A1"].alignment = left_align
    ws.row_dimensions[1].height = 30

    # Headers
    headers = [
        "S.No",
        "Student ID",
        "Roll Number",
        "Student Name",
        "Branch",
        "Aadhar Card",
        "PAN Card",
        "Email ID",
        "Phone Number",
        "Resume Drive Link"
    ]
   
    # In openpyxl: A=1, B=2, C=3, etc. We will write to Row 3
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col_num)
        cell.value = header
        cell.font = white_font
        cell.fill = amber_fill
        cell.alignment = center_align
        cell.border = thin_border
   
    ws.row_dimensions[3].height = 24

    # Data Rows
    for r_idx, app in enumerate(applicants, 1):
        row_num = r_idx + 3
        ws.row_dimensions[row_num].height = 20

        # S.No
        c = ws.cell(row=row_num, column=1, value=r_idx)
        c.font = regular_font
        c.alignment = center_align
        c.border = thin_border

        # Student ID
        c = ws.cell(row=row_num, column=2, value=app["student_id"])
        c.font = bold_font
        c.alignment = center_align
        c.border = thin_border

        # Roll Number
        c = ws.cell(row=row_num, column=3, value=app["roll_number"] or "—")
        c.font = regular_font
        c.alignment = center_align
        c.border = thin_border

        # Name
        c = ws.cell(row=row_num, column=4, value=app["name"])
        c.font = regular_font
        c.alignment = left_align
        c.border = thin_border

        # Branch
        c = ws.cell(row=row_num, column=5, value=app["branch"])
        c.font = regular_font
        c.alignment = center_align
        c.border = thin_border

        # Aadhar
        c = ws.cell(row=row_num, column=6, value=app["aadhar"] or "—")
        c.font = regular_font
        c.alignment = center_align
        c.border = thin_border

        # PAN
        c = ws.cell(row=row_num, column=7, value=app["pan"] or "—")
        c.font = regular_font
        c.alignment = center_align
        c.border = thin_border

        # Email
        c = ws.cell(row=row_num, column=8, value=app["email"])
        c.font = regular_font
        c.alignment = left_align
        c.border = thin_border

        # Phone
        c = ws.cell(row=row_num, column=9, value=app["phone_number"] or "—")
        c.font = regular_font
        c.alignment = center_align
        c.border = thin_border

        # Resume Drive Link
        resume_val = app["resume_path"] or "—"
        c = ws.cell(row=row_num, column=10, value=resume_val)
        c.font = regular_font
        c.alignment = left_align
        c.border = thin_border
        if resume_val.startswith("http"):
            c.hyperlink = resume_val
            c.font = Font(name="Calibri", size=11, color="0000FF", underline="single")

    # Autofit columns
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            # Skip merged cells title length for autofit width calculation
            if cell.row == 1:
                continue
            val_str = str(cell.value or '')
            # If hyperlink, cap length calculation to avoid overly wide column
            if len(val_str) > 30 and cell.column == 10:
                val_str = "https://drive.google.com/..."
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 10)

    # Save to buffer and send
    out = io.BytesIO()
    wb.save(out)
    out.seek(0)

    from flask import send_file
    clean_company = "".join([c for c in company_name if c.isalnum() or c in (' ', '_', '-')]).strip()
    return send_file(
        out,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"Applicants_{clean_company}_{job_id}.xlsx"
    )


# ─── FACULTY: STUDENTS ───────────────────────────────────────────────────────

PREV_YEARS_STATS = {
    "CSE":          {"2023": 94, "2024": 96, "2025": 92},
    "ECE":          {"2023": 86, "2024": 88, "2025": 85},
    "Mechanical":   {"2023": 78, "2024": 82, "2025": 80},
    "Chemical":     {"2023": 72, "2024": 75, "2025": 78},
    "Bio-Technology": {"2023": 70, "2024": 74, "2025": 76},
}

@app.route("/faculty/students")
def faculty_students():
    ensure_connection()
    redir = faculty_required()
    if redir: return redir

    cursor.execute("SELECT branch, COUNT(*) as total FROM students GROUP BY branch")
    branch_counts = {r["branch"]: r["total"] for r in cursor.fetchall()}

    branch_stats = []
    for br in ["CSE", "ECE", "Mechanical", "Chemical", "Bio-Technology"]:
        total = branch_counts.get(br, 0)
        # Approximate placed count via applications
        cursor.execute("""
            SELECT COUNT(DISTINCT a.student_id) as cnt
            FROM applications a
            JOIN students s ON a.student_id = s.student_id
            WHERE s.branch = %s
        """, (br,))
        placed = cursor.fetchone()["cnt"]
        rate = round((placed / total) * 100) if total else 0
        branch_stats.append({"name": br, "total": total, "placed": placed, "rate": rate})

    return render_template("faculty/students.html", branch_stats=branch_stats, branch=None)


@app.route("/faculty/students/<branch_name>")
def faculty_branch_detail(branch_name):
    ensure_connection()
    redir = faculty_required()
    if redir: return redir

    cursor.execute("SELECT * FROM students WHERE branch = %s ORDER BY name", (branch_name,))
    students = cursor.fetchall()

    placed_count = 0
    for s in students:
        cursor.execute("SELECT * FROM applications WHERE student_id=%s", (s["student_id"],))
        s["applications"] = cursor.fetchall()
        if s["applications"]:
            placed_count += 1

    total = len(students)
    current_rate = round((placed_count / total) * 100) if total else 0
    prev_stats = PREV_YEARS_STATS.get(branch_name, {})

    return render_template(
        "faculty/students.html",
        branch=branch_name,
        students=students,
        placed_count=placed_count,
        current_rate=current_rate,
        prev_stats=prev_stats,
        branch_stats=[]
    )


# ─── FACULTY: MASTER SHEET ────────────────────────────────────────────────────
@app.route("/faculty/master_sheet")
def faculty_master_sheet():
    ensure_connection()
    redir = faculty_required()
    if redir: return redir

    return render_template("faculty/master_sheet.html")

@app.route("/faculty/upload_master_sheet", methods=["POST"])
def faculty_upload_master_sheet():
    ensure_connection()

    if "faculty_email" not in session:
        return redirect("/faculty_login")

    file = request.files.get("master_file")

    if not file or file.filename == "":
        flash("Please choose a file first.", "error")
        return redirect("/faculty/master_sheet")

    filename = secure_filename(file.filename)
    upload_folder = os.path.join(app.static_folder, "uploads")
    os.makedirs(upload_folder, exist_ok=True)

    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)

    if filename.lower().endswith(".xlsx"):
        df = pd.read_excel(file_path)

    elif filename.lower().endswith(".csv"):
        df = pd.read_csv(file_path)

    elif filename.lower().endswith(".pdf"):
        all_rows = []

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()

                for table in tables:
                    for row in table:
                        all_rows.append(row)

        if not all_rows:
            return "No table found in PDF. Please upload a proper table PDF."

        headers = all_rows[0]
        data = all_rows[1:]

        df = pd.DataFrame(data, columns=headers)

    else:
        return "Only Excel, CSV, or PDF files are allowed"

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(".", "", regex=False)
        .str.replace(" ", "_")
    )

    print("COLUMNS:", df.columns.tolist())

    updated = 0
    inserted = 0

    for index, row in df.iterrows():
        roll_no = str(row.get("roll_no", "")).strip()
        name = str(row.get("name", "")).strip()
        email = str(row.get("email", "")).strip().lower()
        branch = str(row.get("branch", "")).strip()

        if email == "" or email == "nan":
            continue

        cgpa = float(row.get("cgpa", 0) or 0)
        active_backlogs = int(float(row.get("active_backlogs", 0) or 0))
        backlog_history = int(float(row.get("backlog_history", 0) or 0))
        batch = int(float(row.get("graduation_batch", 0) or 0))
        tenth_score = float(row.get("10th_score", 0) or 0)
        inter_score = float(row.get("inter_score", 0) or 0)

        cursor.execute("SELECT * FROM students WHERE LOWER(email) = %s", (email,))
        existing_student = cursor.fetchone()

        if existing_student:
            cursor.execute("""
                UPDATE students
                SET roll_number = %s,
                    name = %s,
                    cgpa = %s,
                    branch = %s,
                    backlogs = %s,
                    backlog_history = %s,
                    batch = %s,
                    tenth_score = %s,
                    inter_score = %s
                WHERE LOWER(email) = %s
            """, (
                roll_no, name, cgpa, branch,
                active_backlogs, backlog_history, batch,
                tenth_score, inter_score, email
            ))
            updated += 1

        else:
            cursor.execute("SELECT COALESCE(MAX(student_id), 0) + 1 AS next_id FROM students")
            next_id = cursor.fetchone()["next_id"]

            cursor.execute("""
                INSERT INTO students
                (student_id, roll_number, name, email, password, branch, cgpa,
                 backlogs, backlog_history, batch, tenth_score, inter_score, skills,
                 must_change_password)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                next_id, roll_no, name, email, roll_no, branch, cgpa,
                active_backlogs, backlog_history, batch,
                tenth_score, inter_score, "", 1
            ))

            inserted += 1

    db.commit()

    print("UPDATED:", updated)
    print("INSERTED:", inserted)
    flash(f"Master sheet uploaded successfully! {inserted} students added and {updated} students updated.", "success")
    return redirect("/faculty/master_sheet")


@app.route("/faculty/download_master_sheet")
def faculty_download_master_sheet():
    ensure_connection()
    redir = faculty_required()
    if redir: return redir

    from flask import send_file
    upload_dir = os.path.join(app.static_folder, "uploads")
    pdf_path = os.path.join(upload_dir, "master_sheet.pdf")
    xlsx_path = os.path.join(upload_dir, "master_sheet.xlsx")

    if os.path.exists(pdf_path):
        return send_file(pdf_path, as_attachment=True, download_name="master_sheet.pdf")
    elif os.path.exists(xlsx_path):
        return send_file(xlsx_path, as_attachment=True, download_name="master_sheet.xlsx")
    else:
        from flask import flash
        flash("No master sheet file found.", "error")
        return redirect("/faculty/master_sheet")


@app.route("/faculty/delete_master_sheet", methods=["POST"])
def faculty_delete_master_sheet():
    ensure_connection()
    redir = faculty_required()
    if redir: return redir

    from flask import flash
    upload_dir = os.path.join(app.static_folder, "uploads")
    deleted = False
    for fname in ["master_sheet.pdf", "master_sheet.xlsx"]:
        fpath = os.path.join(upload_dir, fname)
        if os.path.exists(fpath):
            os.remove(fpath)
            deleted = True
    if deleted:
        flash("Master sheet deleted successfully.", "success")
    else:
        flash("No master sheet found to delete.", "error")
    return redirect("/faculty/master_sheet")


@app.route("/faculty/upload_students", methods=["POST"])
def faculty_upload_students():
    ensure_connection()
    redir = faculty_required()
    if redir: return redir

    if "file" not in request.files:
        from flask import flash
        flash("No file uploaded.", "error")
        return redirect("/faculty/students")

    file = request.files["file"]
    filename = file.filename.lower()

    if filename.endswith(".xlsx"):
        try:
            import pandas as pd
            df = pd.read_excel(file)
            for index, row in df.iterrows():
                try:
                    row_dict = {str(k).lower().replace(' ', '_'): v for k, v in row.items()}
                    student_id = int(row_dict.get('student_id', 0))
                    name       = str(row_dict.get('name', ''))
                    email      = str(row_dict.get('email', ''))
                    password   = str(row_dict.get('password', email.split('@')[0] if email else 'default123'))
                    branch     = str(row_dict.get('branch', ''))
                    cgpa       = float(row_dict.get('cgpa', 0.0))
                    backlogs   = int(row_dict.get('backlogs', 0))
                    skills     = str(row_dict.get('skills', ''))
                    batch      = int(row_dict.get('batch', 2028))
                    if student_id == 0 or not email:
                        continue
                    cursor.execute("SELECT * FROM students WHERE student_id=%s", (student_id,))
                    if cursor.fetchone():
                        cursor.execute("""UPDATE students SET name=%s,email=%s,branch=%s,cgpa=%s,backlogs=%s,skills=%s,batch=%s WHERE student_id=%s""",
                                       (name,email,branch,cgpa,backlogs,skills,batch,student_id))
                    else:
                        cursor.execute("""INSERT INTO students (student_id,name,email,password,branch,cgpa,backlogs,skills,batch) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                                       (student_id,name,email,password,branch,cgpa,backlogs,skills,batch))
                except Exception as row_err:
                    print(f"Row {index} error: {row_err}")
            db.commit()
            from flask import flash
            flash("Students updated successfully from Excel!", "success")
        except Exception as e:
            from flask import flash
            flash(f"Failed to process Excel: {str(e)}", "error")
    else:
        from flask import flash
        flash("Please upload a .xlsx Excel file.", "error")

    return redirect("/faculty/students")


# ─── FORGOT PASSWORD ─────────────────────────────────────────────────────────

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        if not email:
            from flask import flash
            flash("Please enter an email address.", "error")
            return redirect("/forgot_password")
       
        # Check students table
        cursor.execute("SELECT * FROM students WHERE email=%s", (email,))
        student = cursor.fetchone()
       
        # Check faculty table
        cursor.execute("SELECT * FROM faculty WHERE email=%s", (email,))
        faculty = cursor.fetchone()
       
        if not student and not faculty:
            from flask import flash
            flash("No account found with that email address.", "error")
            return redirect("/forgot_password")
           
        role = "student" if student else "faculty"
       
        # Generate 6 digit OTP
        import random
        otp = str(random.randint(100000, 999999))
        session['reset_email'] = email
        session['reset_role'] = role
        session['reset_otp'] = otp
       
        # Mocking email send by flashing it directly
        from flask import flash
        flash(f"MOCK EMAIL SEND: Your OTP is {otp}", "info")
        return redirect("/verify_otp")
       
    return render_template("forgot_password.html")

@app.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():
    if 'reset_email' not in session:
        return redirect("/forgot_password")
       
    if request.method == "POST":
        entered_otp = request.form.get("otp", "").strip()
        if entered_otp == session.get('reset_otp'):
            session['reset_verified'] = True
            return redirect("/reset_password")
        else:
            from flask import flash
            flash("Invalid OTP. Please try again.", "error")
           
    return render_template("verify_otp.html", email=session.get('reset_email'))

@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if not session.get('reset_verified') or 'reset_email' not in session:
        return redirect("/forgot_password")
       
    if request.method == "POST":
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
       
        if len(new_password) < 6:
            from flask import flash
            flash("Password must be at least 6 characters long.", "error")
            return redirect("/reset_password")
           
        if new_password != confirm_password:
            from flask import flash
            flash("Passwords do not match.", "error")
            return redirect("/reset_password")
           
        email = session['reset_email']
        role = session['reset_role']
       
        try:
            if role == "student":
                cursor.execute("UPDATE students SET password=%s WHERE email=%s", (new_password, email))
            else:
                cursor.execute("UPDATE faculty SET password=%s WHERE email=%s", (new_password, email))
            db.commit()
           
            # Clear session
            session.pop('reset_email', None)
            session.pop('reset_role', None)
            session.pop('reset_otp', None)
            session.pop('reset_verified', None)
           
            from flask import flash
            flash("Password has been reset successfully! You can now log in.", "success")
            return redirect("/")
        except Exception as e:
            db.rollback()
            from flask import flash
            flash(f"An error occurred: {str(e)}", "error")
           
    return render_template("reset_password.html")

if __name__ == "__main__":
    app.run(debug=True)