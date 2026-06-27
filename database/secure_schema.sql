-- secure_schema.sql
-- Add columns to users table
ALTER TABLE users
  ADD COLUMN password_hash VARCHAR(255) NOT NULL AFTER email,
  ADD COLUMN role ENUM('student','faculty','admin') NOT NULL DEFAULT 'student' AFTER password_hash,
  ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT FALSE AFTER role,
  ADD COLUMN is_verified BOOLEAN NOT NULL DEFAULT FALSE AFTER is_active,
  ADD COLUMN email_otp VARCHAR(6) NULL AFTER is_verified,
  ADD COLUMN otp_expiry DATETIME NULL AFTER email_otp,
  ADD COLUMN failed_attempts INT NOT NULL DEFAULT 0 AFTER otp_expiry,
  ADD COLUMN lock_until DATETIME NULL AFTER failed_attempts;

-- OTP table (single source of truth for all OTP purposes)
CREATE TABLE email_otps (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  otp VARCHAR(6) NOT NULL,
  purpose ENUM('registration','password_reset','2fa') NOT NULL,
  expires_at DATETIME NOT NULL,
  used BOOLEAN NOT NULL DEFAULT FALSE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Activity logs
CREATE TABLE activity_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  role VARCHAR(20) NOT NULL,
  action VARCHAR(100) NOT NULL,
  ip_address VARCHAR(45) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Faculty approval workflow
CREATE TABLE faculty_approvals (
  id INT AUTO_INCREMENT PRIMARY KEY,
  faculty_user_id INT NOT NULL,
  approved_by_admin_id INT NULL,
  status ENUM('pending','approved','rejected') NOT NULL DEFAULT 'pending',
  decision_at DATETIME NULL,
  FOREIGN KEY (faculty_user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (approved_by_admin_id) REFERENCES users(id) ON DELETE SET NULL
);
