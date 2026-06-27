# Job Follow-Up Reminders Implementation Plan

## Goal
Add a feature allowing faculty to set follow-up reminders for specific companies/jobs (e.g., to contact HR). When the reminder date arrives, the faculty should see an alert in the portal and receive an email notification.

## Open Questions
- Should the email be sent to the `SMTP_EMAIL` address, or does each faculty member have their own email in the `faculty` table? (I will default to the currently logged-in faculty's email, or fallback to `SMTP_EMAIL`).
- Currently, background tasks are not running a cron loop. I plan to check for due reminders whenever the faculty loads the Dashboard. This means if you don't log in on that exact date, the email will send the next time you log in. Is this acceptable? 

## Proposed Changes

### Database Updates
- **`jobs` table:** Add three new columns:
  - `reminder_date` (DATETIME)
  - `reminder_note` (TEXT)
  - `reminder_sent` (TINYINT default 0)

### Backend (`app.py`)
- **[MODIFY] `init_batch_db()`**: Add the new columns to the `jobs` table schema.
- **[NEW ROUTE] `/faculty/set_job_reminder`**: Endpoint to save the reminder date and note for a specific job.
- **[MODIFY] `/faculty_dashboard`**: When this page is loaded, query the database for any jobs where `reminder_date <= NOW()` and `reminder_sent = 0`. For each one:
  - Add an alert to the dashboard UI.
  - Send an email notification to the faculty email.
  - Update `reminder_sent = 1` in the database.

### Frontend (`templates/faculty/jobs.html`)
- **[MODIFY] Job Card**: Add a "⏰ Set Reminder" button next to edit/delete buttons.
- **[NEW] Reminder Modal**: A modal containing a Date picker and a Textarea for the reminder note.
- **[MODIFY] JavaScript**: Add functions to open the modal and submit the reminder via fetch to `/faculty/set_job_reminder`.

### Frontend (`templates/faculty/dashboard.html`)
- **[MODIFY] Dashboard UI**: Add a section (or alerts at the top) displaying "🔔 Pending Follow-ups" if any reminders are due today or overdue.

## Verification Plan
1. Manually set a reminder for a job with a date in the past.
2. Navigate to the Faculty Dashboard.
3. Verify the dashboard shows the reminder alert.
4. Verify an email was dispatched to the faculty.
