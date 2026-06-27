# Job Follow-Up Reminders Checklist

- [x] **Database Schema Updates**
  - [x] Add `reminder_date`, `reminder_note`, `reminder_sent` columns to `jobs` table in `init_batch_db()`.
  - [x] Create and run a migration script to add these columns to existing databases.

- [x] **Backend Implementation (`app.py`)**
  - [x] Create `/faculty/set_job_reminder` route to save reminder data.
  - [x] Implement a background thread `start_reminder_scheduler()` that checks for due reminders every 10 minutes across all batch databases.
  - [x] Call `send_email()` from the background thread using the `SMTP_EMAIL` address.

- [x] **Frontend Implementation (`jobs.html`)**
  - [x] Add a "⏰ Set Reminder" button to each job card.
  - [x] Add a modal for setting the reminder (Date/Time picker, Note textarea).
  - [x] Add JS fetch logic to send reminder data to `/faculty/set_job_reminder`.

- [x] **Dashboard Implementation (`dashboard.html`)**
  - [x] Add a "Pending Reminders" widget to the faculty dashboard, fetching due reminders.
