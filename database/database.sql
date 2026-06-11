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

UPDATE students
SET selected_tier = NULL
WHERE email = 'pallavi123@gmail.com';

SELECT * FROM students;
SELECT student_id, name, email FROM students;
INSERT INTO students(student_id, name, email, password, branch, cgpa, backlogs, skills, selected_tier, batch)
VALUES
(1,"Pallavi", "pallavi123@gmail.com", "pallavi123", "AI", 9.2, 0, "Java, DSA, Full Stack Development", 1, 2028);

INSERT INTO students(student_id, name, email, password, branch, cgpa, backlogs, skills, selected_tier, batch)
VALUES
(2,"linda", "linda123@gmail.com", "linda123", "CSE", 9.1, 0, "C, CPP, HTML, CSS, MySQL",2, 2029);

INSERT INTO students(student_id, name, email, password, branch, cgpa, backlogs, skills, selected_tier, batch)
VALUES
(3,"Hasini", "hasini123@gmail.com", "hasini123", "CSE", 9.5, 0, "HTML, CSS, JS, Python, C, CPP", 1, 2029);

CREATE TABLE faculty(
    faculty_id INT PRIMARY KEY,
    name VARCHAR(50),
    email VARCHAR(100),
    password VARCHAR(50)
    );
    
INSERT INTO faculty (faculty_id, name, email, password)
VALUES (1, 'Dr. Shankar', 'drshankar@gmail.com', 'shankar123');

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