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

CREATE TABLE applications(
	application_id INT PRIMARY KEY,
    student_id INT PRIMARY KEY,
    job_id INT PRIMARY KEY,
    resume_path TEXT,
    status TEXT,
    applied_date DATE
);