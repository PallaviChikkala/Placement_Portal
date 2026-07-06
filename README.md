# 🎓 University Placement Portal

A modern, web-based Placement Portal designed to streamline the campus recruitment process. The system connects students and faculty through a centralized platform, automating eligibility checks, application tracking, and placement drive management.

---

## ✨ Key Features

### 👨‍🎓 Student Module
- **Dashboard**: Centralized view of placement status and updates.
- **Job Opportunities**: Browse and filter available jobs.
- **One-Click Apply**: Apply for jobs seamlessly.
- **Eligibility Verification**: Automated eligibility checks based on academic records.
- **Application Tracking**: Track the status of ongoing and past applications.
- **Resume Analyzer**: Built-in tool for analyzing and improving resumes.

### 👨‍🏫 Faculty/Admin Module
- **Admin Dashboard**: Comprehensive overview of placement statistics.
- **Manage Jobs**: Post, edit, and delete job opportunities.
- **Drive Management**: Configure eligibility criteria (CGPA, backlogs, branch, etc.) for recruitment drives.
- **Student Applications**: Review and manage student applications.
- **Automated Notifications**: Scheduled reminders and email notifications to students.

---

## 🛠️ Technologies Used

- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap
- **Backend**: Python, Flask
- **Database**: MySQL
- **Email Service**: SMTP Integration

---

## 🚀 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/PallaviChikkala/Placement_Portal.git
   cd Placement_Portal
   ```

2. **Set up a virtual environment (optional but recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   Rename `.env.example` to `.env` and update it with your actual credentials:
   ```env
   SMTP_EMAIL=your_email@example.com
   SMTP_PASSWORD=your_app_password
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   PORTAL_URL=http://127.0.0.1:5000
   PORTAL_NAME="University Placement Portal"
   ```

5. **Run the application:**
   ```bash
   python app.py
   ```
   The portal should now be running at `http://127.0.0.1:5000`.

---

## 🔮 Future Enhancements
- Advanced Interview Scheduling System
- Placement Statistics & Analytics Dashboard
- AI-Based Job Recommendations for Students
- Advanced ATS Resume Scoring

---

*Developed as an academic project to demonstrate Full Stack Web Development using Flask and MySQL by Pallavi Chikkala and Hasini.*
