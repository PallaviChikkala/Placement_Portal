from flask import Flask, request, render_template, redirect, session
import pdfplumber
import docx
import mysql.connector

app = Flask(__name__)
app.secret_key = "placement_portal_secret"

#MYSQL Connection
db = mysql.connector.connect(
    host = "localhost",
    user = "root",
    password = "Pallavi@2007",
    database = "placement_portal"
 )

cursor = db.cursor(dictionary = True)

# Database Tables & Mock Data Initialization
def init_database():
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
                batch INT
            )
        """)
        
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
                job_id INT PRIMARY KEY,
                company_name VARCHAR(50),
                role VARCHAR(50) NOT NULL,
                package_lpa DECIMAL(7,2),
                tier VARCHAR(20),
                eligible_branches TEXT,
                min_cgpa DECIMAL(3,2),
                max_backlogs INT DEFAULT 0,
                required_skills TEXT,
                job_description TEXT,
                deadline DATE
            )
        """)
        
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
                INSERT INTO jobs (job_id, company_name, role, package_lpa, tier, eligible_branches, min_cgpa, max_backlogs, required_skills, job_description, deadline)
                VALUES 
                (1, 'TCS', 'Software Developer', 7.00, 'Tier 2', 'AI, CSE, ECE, EEE', 7.00, 0, 'Java, HTML, CSS, SQL', 'Join the TCS digital developer team to work on next-generation cloud architectures.', '2026-06-10'),
                (2, 'Infosys', 'Specialist Programmer', 20.00, 'Tier 1', 'CSE, IT', 9.50, 0, 'Java, DSA, Web Development', 'High performance developer role working on core software products and algorithmic scaling.', '2026-06-15'),
                (3, 'Wipro', 'Full Stack Developer', 8.00, 'Tier 2', 'AI, CSE, ECE', 6.50, 1, 'HTML, CSS, JavaScript, React', 'Design and implement web interfaces and microservice endpoints in our digital unit.', '2026-06-18')
            """)
            
        db.commit()
        print("Database tables and mock data initialized successfully.")
    except Exception as e:
        print("Warning: Database initialization failed. Details:", e)

init_database()


@app.route("/")
def home():
    return '''
        <form action = "/upload" method = "POST" enctype = "multipart/form-data">

         <select name = "role">
            <option>Select role</option>
            <option>Frontend Developer</option>
            <option>Backend Developer</option>
            <option>Full Stack Developer</option>
            <option>Java Developer</option>
            <option>Python Developer</option>
            <option>C++ Developer</option>
            <option>Software Developer</option>
            <option>Web Developer</option>
            <option>Mobile App Developer</option>
            <option>Android Developer</option>
            <option>iOS Developer</option>
            <option>React Developer</option>
            <option>Angular Developer</option>
            <option>Node.js Developer</option>
            <option>PHP Developer</option>
            <option>.NET Developer</option>
            <option>Database Administrator(DBA)</option>
            <option>SQL Developer</option>
            <option>Data Analyst</option>
            <option>Business Analyst</option>
            <option>Data Scientist</option>
            <option>Machine Learning Engineer</option>
            <option>AI Engineer</option>
            <option>Deep Learning Engineer</option>
            <option>Cloud Engineer</option>
            <option>DevOps Engineer</option>
            <option>Cybersecurity Engineer</option>
            <option>Network Engineer</option>
            <option>Software Test Engineer</option>
            <option>UI/UX Designer</option>
        </select>

            <input type = "file" name = "resume" placeholder = "Upload resume"/><br>
            <button type = "submit">Analyze resume</button>
        </form>
'''

@app.route("/upload",methods = ["POST"])
def upload():
    file = request.files["resume"]
    filename = file.filename.lower()
    role = request.form["role"]
    
    if role == "Select role":
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
    }
    }

    selected_role = role_skills[role]
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

    query = "SELECT * FROM students WHERE email = %s AND password = %s"
    cursor.execute(query, (email,password))
    student = cursor.fetchone()

    if student: 
        session["student_id"] = student["student_id"]
        session["student_name"] = student["name"]
        return redirect("/student_dashboard")
    else :
        return """
        <script>
            alert("Invalid email or password!");
            window.location.href = "/student_login";
        </script>
        """

@app.route("/forgot_password")
def forgot_password_page():
    return render_template("student/forgot_password.html")

@app.route("/send_verification_code", methods=["POST"])
def send_verification_code():
    email = request.form.get("email")
    
    # Check if email exists in database
    cursor.execute("SELECT * FROM students WHERE email = %s", (email,))
    student = cursor.fetchone()
    
    if not student:
        return """
        <script>
            alert("Email not found in student records.");
            window.location.href = "/forgot_password";
        </script>
        """
        
    import random
    code = str(random.randint(100000, 999999))
    session["reset_code"] = code
    session["reset_email"] = email
    
    # Simulating sending email by printing code to python console
    print("\n" + "="*50)
    print(f"PASSWORD RESET CODE FOR {email}: {code}")
    print("="*50 + "\n")
    
    # Storing code in a temporary cookie/session variable to display as a simulated alert on verify page
    session["simulated_sent_code"] = code
    
    return redirect("/verify_code")

@app.route("/verify_code")
def verify_code_page():
    if "reset_email" not in session:
        return redirect("/forgot_password")
    # Retrieve simulated code to show it in an alert box for easy user testing
    simulated_code = session.get("simulated_sent_code")
    return render_template("student/verify_code.html", email=session["reset_email"], simulated_code=simulated_code)

@app.route("/reset_password", methods=["POST"])
def reset_password_action():
    if "reset_email" not in session:
        return redirect("/forgot_password")
        
    entered_code = request.form.get("code")
    new_password = request.form.get("password")
    email = session["reset_email"]
    
    if entered_code != session.get("reset_code"):
        return """
        <script>
            alert("Invalid verification code. Please try again.");
            window.location.href = "/verify_code";
        </script>
        """
        
    # Update password in DB
    cursor.execute("UPDATE students SET password = %s WHERE email = %s", (new_password, email))
    db.commit()
    
    # Clear session reset keys
    session.pop("reset_code", None)
    session.pop("reset_email", None)
    session.pop("simulated_sent_code", None)
    
    return """
    <script>
        alert("Password reset successful! Please login with your new password.");
        window.location.href = "/student_login";
    </script>
    """

@app.route("/student_dashboard")
def student_dashboard():
    if "student_id" not in session:
        return redirect("/student_login")
        
    student_id = session["student_id"]
    
    # Fetch student data
    cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()
    if not student:
        session.clear()
        return redirect("/student_login")
    
    # Fetch all jobs to evaluate eligibility count
    cursor.execute("SELECT * FROM jobs")
    all_jobs = cursor.fetchall()
    
    eligible_count = 0
    upcoming_drives = []
    
    for job in all_jobs:
        # Determine job tier dynamically from package
        package = float(job['package_lpa']) if job['package_lpa'] is not None else 0
        if package > 15:
            job_tier_num = 1
        elif package >= 7:
            job_tier_num = 2
        else:
            job_tier_num = 3

        # Eligibility logic
        eligible_branches = [b.strip().lower() for b in job['eligible_branches'].split(',')] if job['eligible_branches'] else []
        student_branch = student['branch'].strip().lower() if student['branch'] else ""
        
        cgpa_ok = student['cgpa'] >= float(job['min_cgpa']) if student['cgpa'] is not None and job['min_cgpa'] is not None else True
        backlogs_ok = student['backlogs'] <= int(job['max_backlogs']) if student['backlogs'] is not None and job['max_backlogs'] is not None else True
        branch_ok = (student_branch in eligible_branches) or (not eligible_branches)
        
        # Tier check
        student_selected_tier = student.get('selected_tier')
        tier_ok = True
        if student_selected_tier is not None and student_selected_tier > 0:
            if student_selected_tier == 1 and job_tier_num in [2, 3]:
                tier_ok = False
            elif student_selected_tier == 2 and job_tier_num in [2, 3]:
                tier_ok = False
            elif student_selected_tier == 3 and job_tier_num == 3:
                tier_ok = False

        is_eligible = cgpa_ok and backlogs_ok and branch_ok and tier_ok
        if is_eligible:
            eligible_count += 1
        
        # Attach eligibility flag to job for display
        job_copy = dict(job)
        job_copy['is_eligible'] = is_eligible
        upcoming_drives.append(job_copy)
    
    # Sort upcoming drives by deadline
    upcoming_drives = sorted(upcoming_drives, key=lambda x: str(x['deadline']))[:5]
    
    # Fetch count of applied companies
    cursor.execute("SELECT COUNT(*) as count FROM applications WHERE student_id = %s", (student_id,))
    applied_count = cursor.fetchone()['count']
    
    # Fetch count of interview calls
    cursor.execute("SELECT COUNT(*) as count FROM applications WHERE student_id = %s AND status = 'Interview'", (student_id,))
    interview_count = cursor.fetchone()['count']
    
    # Fetch recent applications
    cursor.execute("""
        SELECT a.applied_date, a.status, j.company_name, j.role, j.package_lpa 
        FROM applications a 
        JOIN jobs j ON a.job_id = j.job_id 
        WHERE a.student_id = %s 
        ORDER BY a.applied_date DESC LIMIT 5
    """, (student_id,))
    recent_applications = cursor.fetchall()
    
    # Resume score from session or default
    resume_score = session.get("resume_score", 0)
    
    return render_template(
        "student/dashboard.html",
        name=student["name"],
        student=student,
        eligible_count=eligible_count,
        applied_count=applied_count,
        interview_count=interview_count,
        resume_score=resume_score,
        upcoming_drives=upcoming_drives,
        recent_applications=recent_applications
    )

@app.route("/student_profile")
def student_profile():
    if "student_id" not in session:
        return redirect("/student_login")

    student_id = session["student_id"]

    query = "SELECT * FROM students WHERE student_id = %s"
    cursor.execute(query, (student_id,))
    student = cursor.fetchone()

    return render_template("student/profile.html", student=student)

@app.route("/update_profile", methods=["POST"])
def update_profile():
    if "student_id" not in session:
        return redirect("/student_login")
        
    student_id = session["student_id"]
    
    name = request.form.get("name")
    email = request.form.get("email")
    branch = request.form.get("branch")
    cgpa = request.form.get("cgpa")
    backlogs = request.form.get("backlogs")
    skills = request.form.get("skills")
    batch = request.form.get("batch")
    
    query = """
        UPDATE students 
        SET name = %s, email = %s, branch = %s, cgpa = %s, backlogs = %s, skills = %s, batch = %s
        WHERE student_id = %s
    """
    cursor.execute(query, (name, email, branch, cgpa, backlogs, skills, batch, student_id))
    db.commit()
    
    session["student_name"] = name
    
    return redirect("/student_profile")

@app.route("/eligible_companies")
def eligible_companies():
    if "student_id" not in session:
        return redirect("/student_login")
    
    student_id = session["student_id"]
    cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()
    
    cursor.execute("SELECT * FROM jobs")
    all_jobs = cursor.fetchall()
    
    # Check eligibility for each job
    jobs_list = []
    for job in all_jobs:
        package = float(job['package_lpa']) if job['package_lpa'] is not None else 0
        if package > 15:
            job_tier_num = 1
        elif package >= 7:
            job_tier_num = 2
        else:
            job_tier_num = 3

        eligible_branches = [b.strip().lower() for b in job['eligible_branches'].split(',')] if job['eligible_branches'] else []
        student_branch = student['branch'].strip().lower() if student['branch'] else ""
        
        cgpa_ok = student['cgpa'] >= float(job['min_cgpa']) if student['cgpa'] is not None and job['min_cgpa'] is not None else True
        backlogs_ok = student['backlogs'] <= int(job['max_backlogs']) if student['backlogs'] is not None and job['max_backlogs'] is not None else True
        branch_ok = (student_branch in eligible_branches) or (not eligible_branches)
        
        # Tier check
        student_selected_tier = student.get('selected_tier')
        tier_ok = True
        if student_selected_tier is not None and student_selected_tier > 0:
            if student_selected_tier == 1 and job_tier_num in [2, 3]:
                tier_ok = False
            elif student_selected_tier == 2 and job_tier_num in [2, 3]:
                tier_ok = False
            elif student_selected_tier == 3 and job_tier_num == 3:
                tier_ok = False

        reasons = []
        if not cgpa_ok:
            reasons.append(f"CGPA below requirement ({student['cgpa']} < {job['min_cgpa']})")
        if not backlogs_ok:
            reasons.append(f"Backlogs exceed maximum allowed ({student['backlogs']} > {job['max_backlogs']})")
        if not branch_ok:
            reasons.append(f"Branch not eligible (Your branch: {student['branch'].upper()}, Eligible: {job['eligible_branches']})")
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
        jobs_list.append(job_item)
        
    return render_template("student/eligible_companies.html", jobs=jobs_list, student=student)

@app.route("/apply_job", methods=["POST"])
def apply_job():
    if "student_id" not in session:
        return redirect("/student_login")
    
    student_id = session["student_id"]
    job_id = request.form.get("job_id")
    
    # Fetch student and job details to verify tier restrictions in backend
    cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()
    cursor.execute("SELECT * FROM jobs WHERE job_id = %s", (job_id,))
    job = cursor.fetchone()
    
    if not student or not job:
        return "Invalid request."
        
    # Tier calculation
    package = float(job['package_lpa']) if job['package_lpa'] is not None else 0
    if package > 15:
        job_tier_num = 1
    elif package >= 7:
        job_tier_num = 2
    else:
        job_tier_num = 3
        
    student_selected_tier = student.get('selected_tier')
    tier_ok = True
    if student_selected_tier is not None and student_selected_tier > 0:
        if student_selected_tier == 1 and job_tier_num in [2, 3]:
            tier_ok = False
        elif student_selected_tier == 2 and job_tier_num in [2, 3]:
            tier_ok = False
        elif student_selected_tier == 3 and job_tier_num == 3:
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
    
    query = """
        INSERT INTO applications (application_id, student_id, job_id, resume_path, status, applied_date) 
        VALUES (%s, %s, %s, %s, %s, CURDATE())
    """
    cursor.execute(query, (next_id, student_id, job_id, "Uploaded Resume", "Pending"))
    db.commit()
    
    return """
    <script>
        alert("Application submitted successfully!");
        window.location.href = "/my_applications";
    </script>
    """

@app.route("/my_applications")
def my_applications():
    if "student_id" not in session:
        return redirect("/student_login")
        
    student_id = session["student_id"]
    cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()
    
    query = """
        SELECT a.applied_date, a.status, a.resume_path, 
               j.company_name, j.role, j.package_lpa, j.tier, j.deadline
        FROM applications a
        JOIN jobs j ON a.job_id = j.job_id
        WHERE a.student_id = %s
        ORDER BY a.applied_date DESC
    """
    cursor.execute(query, (student_id,))
    apps = cursor.fetchall()
    
    return render_template("student/my_applications.html", applications=apps, student=student)

@app.route("/student_logout")
def student_logout():
    session.clear()
    return redirect("/student_login")


if __name__ == "__main__":
    app.run(debug = True)
