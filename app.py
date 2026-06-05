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
    
    return f"""
        Selected role : {role}<br>

        Found required skills : {found_required}<br>
        Missing required skills : {missing_required}<br>

        Found optional skills : {found_optional}<br>
        Missing optional skills : {missing_optional}<br>

        ATS Score : {score}%<br>
        Genome Score : {genome_score}%<br>
        Suggestion : {suggestion}<br>
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
        return "Invalid email or password"
    
    
@app.route("/student_dashboard")
def student_dashboard():
    if "student_id" not in session:
        return redirect("/student_login")
    return render_template(
    "student/dashboard.html",
    name=session["student_name"]
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

@app.route("/student_logout")
def student_logout():
    session.clear()
    return redirect("/student_login")


if __name__ == "__main__":
    app.run(debug = True)