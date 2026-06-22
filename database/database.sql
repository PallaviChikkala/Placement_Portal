CREATE DATABASE IF NOT EXISTS placement_portal;
USE placement_portal;

CREATE TABLE students(
	student_id INT PRIMARY KEY,
    name VARCHAR(50),
    email VARCHAR(100),
    password VARCHAR(50),
    branch VARCHAR(50),
    cgpa FLOAT,
    backlogs INT,
    skills TEXT,
    selected_tier INT DEFAULT NULL
);

ALTER TABLE students 
ADD batch INT;

ALTER TABLE students ADD COLUMN tenth_score FLOAT;
ALTER TABLE students ADD COLUMN inter_score FLOAT;

UPDATE students
SET selected_tier = NULL
WHERE email = 'pallavi123@gmail.com';

SELECT * FROM students;

SELECT student_id, name, must_change_password
FROM students;

UPDATE students
SET must_change_password = 0
WHERE student_id IN (1,2,3,4,5,6,7);

UPDATE students
SET must_change_password = 1
WHERE student_id = 8;

SELECT student_id, name, email FROM students;
INSERT INTO students(student_id, name, email, password, branch, cgpa, backlogs, skills, selected_tier, batch)
VALUES
(1,"Pallavi", "pallavi123@gmail.com", "pallavi123", "AI", 9.2, 0, "Java, DSA, Full Stack Development", 1, 2028);

INSERT INTO students(student_id, name, email, password, branch, cgpa, backlogs, skills, selected_tier, batch)
VALUES
(2,"linda", "linda123@gmail.com", "linda123", "CSE", 9.1, 0, "C, CPP, HTML, CSS, MySQL",2, 2029);
INSERT INTO students(student_id, name, email, password, branch, cgpa, backlogs, skills, selected_tier, batch)
VALUES
(3, 'Hasini', 'hasini123@gmail.com', 'hasini123', 'CSE', 9.5, 0, 'HTML, CSS, JS, Python, C, CPP', 1, 2029);

INSERT INTO students(student_id, name, email, password, branch, cgpa, backlogs, skills, selected_tier, batch)
VALUES
(4,'elsa','elsa123@gmail.com','elsa123','mechanical',9.7,0,'CAD,Thermodynamic,Robotics',2,2029);

CREATE TABLE faculty(
    faculty_id INT PRIMARY KEY,
    name VARCHAR(50),
    email VARCHAR(100),
    password VARCHAR(50)
    );
    
INSERT INTO faculty (faculty_id, name, email, password)
VALUES (1, 'Dr. Shankar', 'drshankar@gmail.com', 'shankar123');

DELETE FROM faculty
WHERE faculty_id = 1;

INSERT INTO faculty (faculty_id, name, email, password)
VALUES
(1, 'Placement Officer', 'tap@nitandhra.ac.in', 'placementOfficerNITandhra2015'),
(2, 'Placement Officer', 'tapc@nitandhra.ac.in', 'placementOfficerNITandhra2015');

SELECT * FROM faculty;

CREATE TABLE recruiters(
	recruiter_id INT PRIMARY KEY,
    company_name VARCHAR(50),
    email VARCHAR(100),
    password VARCHAR(50)
    );
    
CREATE TABLE jobs(
    job_id INT PRIMARY KEY,
    company_name VARCHAR(50),
    role VARCHAR(50) NOT NULL,
    package_lpa DECIMAL(7,2),
    tier ENUM('Tier 1','Tier 2','Tier 3'),
    eligible_branches TEXT,
    min_cgpa DECIMAL(3,2),
    max_backlogs INT DEFAULT 0,
    required_skills TEXT,
    job_description TEXT,
    deadline DATE
    );

SELECT * FROM jobs;

CREATE TABLE applications(
    application_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT,
    job_id INT,
    resume_path TEXT,
    status TEXT,
    applied_date DATE
);
SELECT * FROM applications;

DELETE FROM applications
WHERE application_id IN (4, 5, 6);

INSERT INTO applications(student_id, job_id, resume_path, status, applied_date)
VALUES
(1, 3, 'https://drive.google.com/file/d/1kChVucIoPUWM5I02XY7vr24zYct8XRlS/view?usp=sharing', 'Pending', '2026-06-10'),
(3, 2, 'https://drive.google.com/file/d/1kChVucIoPUWM5I02XY7vr24zYct8XRlS/view?usp=sharing', 'Pending', '2026-06-10'),
(3, 4, 'https://drive.google.com/file/d/1kChVucIoPUWM5I02XY7vr24zYct8XRlS/view?usp=sharing', 'Pending', '2026-06-10');