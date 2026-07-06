"""
email_service.py — Placement Portal Email Notification Service
===============================================================
Sends professional HTML emails to students using their registered
email addresses (stored in the students database via master sheet upload).

Transport: Gmail SMTP (TLS, port 587)
Credentials: Loaded from .env file
Async: Uses threading so the admin UI never blocks
"""

import smtplib
import threading
import time
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ── Load credentials from .env ─────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    import os
    load_dotenv()
except ImportError:
    import os  # dotenv not installed — fall back to real env vars

SMTP_HOST     = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.environ.get("SMTP_PORT", "587"))
SMTP_EMAIL    = os.environ.get("SMTP_EMAIL", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
PORTAL_URL    = os.environ.get("PORTAL_URL", "https://university.edu/placement")
PORTAL_NAME   = os.environ.get("PORTAL_NAME", "University Placement Portal")

# Rate limiting: seconds between emails in a bulk send
RATE_LIMIT_DELAY = 0.15   # 150ms between sends
MAX_BULK_PER_BATCH = 100  # cap per trigger to avoid Gmail quota issues


def is_configured() -> bool:
    """Return True only if SMTP credentials are set AND not placeholder values."""
    PLACEHOLDERS = {
        'your_gmail@gmail.com', 'your_email@gmail.com',
        'your_16_char_app_password', 'your_app_password', '', 'none', 'null'
    }
    email_ok = bool(SMTP_EMAIL) and SMTP_EMAIL.lower() not in PLACEHOLDERS and '@' in SMTP_EMAIL
    pass_ok  = bool(SMTP_PASSWORD) and SMTP_PASSWORD.lower() not in PLACEHOLDERS and len(SMTP_PASSWORD) >= 8
    return email_ok and pass_ok


def validate_email(email: str) -> bool:
    """Basic email validation."""
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, str(email).strip()))


# ── Low-level sender ───────────────────────────────────────────────────────

def send_email(to_email: str, subject: str, html_body: str, attachments: list = None) -> dict:
    """
    Send a single HTML email.
    Returns {'success': True} or {'success': False, 'error': '...'}.
    """
    if not is_configured():
        return {'success': False, 'error': 'SMTP not configured. Set SMTP_EMAIL and SMTP_PASSWORD in .env'}

    if not validate_email(to_email):
        return {'success': False, 'error': f'Invalid email address: {to_email}'}

    try:
        msg = MIMEMultipart('mixed') if attachments else MIMEMultipart('alternative')
        import email.utils
        msg['Subject'] = subject
        msg['From']    = f"{PORTAL_NAME} <{SMTP_EMAIL}>"
        msg['To']      = to_email
        msg['Reply-To']= SMTP_EMAIL
        msg['Date']    = email.utils.formatdate(localtime=True)
        msg['Message-ID'] = email.utils.make_msgid(domain=SMTP_EMAIL.split('@')[-1] if '@' in SMTP_EMAIL else 'placementportal.com')

        plain = re.sub(r'<[^>]+>', '', html_body).strip()

        if attachments:
            alt_part = MIMEMultipart('alternative')
            alt_part.attach(MIMEText(plain, 'plain'))
            alt_part.attach(MIMEText(html_body, 'html'))
            msg.attach(alt_part)
            
            from email.mime.application import MIMEApplication
            for filename, file_data in attachments:
                part = MIMEApplication(file_data, Name=filename)
                part['Content-Disposition'] = f'attachment; filename="{filename}"'
                msg.attach(part)
        else:
            msg.attach(MIMEText(plain, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_string())

        return {'success': True}

    except smtplib.SMTPAuthenticationError:
        return {'success': False, 'error': 'SMTP authentication failed. Check your App Password.'}
    except smtplib.SMTPRecipientsRefused:
        return {'success': False, 'error': f'Recipient refused: {to_email}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ── Bulk sender (async via thread) ─────────────────────────────────────────

def send_bulk_emails_async(recipients: list, subject: str, html_body_fn,
                           log_callback=None, db_config=None, event_type="general", attachments=None):
    """
    Send emails to a list of recipient dicts asynchronously.
    
    Args:
        recipients:   list of {'email': str, 'name': str, 'student_id': int}
        subject:      Email subject line
        html_body_fn: Callable(recipient_dict) -> HTML string
        log_callback: Optional function(student_id, email, status, error) to log results
        db_config:    Optional dict with db connection params for logging
        event_type:   String label for email logs (e.g. 'new_job', 'status_update')
    """
    def _send_all():
        sent_count   = 0
        failed_count = 0
        seen_emails  = set()

        capped = recipients[:MAX_BULK_PER_BATCH]

        for rec in capped:
            email = str(rec.get('email', '')).strip().lower()
            name  = rec.get('name', 'Student')
            sid   = rec.get('student_id', None)

            # Deduplication within this batch
            if email in seen_emails:
                continue
            seen_emails.add(email)

            if not validate_email(email):
                if log_callback:
                    log_callback(sid, email, 'failed', 'Invalid email address')
                failed_count += 1
                continue

            try:
                body   = html_body_fn(rec)
                result = send_email(email, subject, body, attachments=attachments)

                status = 'sent' if result['success'] else 'failed'
                err    = result.get('error', None) if not result['success'] else None

                if log_callback:
                    log_callback(sid, email, status, err)

                if result['success']:
                    sent_count += 1
                else:
                    failed_count += 1
                    print(f"[EmailService] Failed to send to {email}: {err}")

            except Exception as ex:
                failed_count += 1
                print(f"[EmailService] Exception sending to {email}: {ex}")
                if log_callback:
                    log_callback(sid, email, 'failed', str(ex))

            time.sleep(RATE_LIMIT_DELAY)

        print(f"[EmailService] Bulk send complete — sent: {sent_count}, failed: {failed_count}")

    thread = threading.Thread(target=_send_all, daemon=True)
    thread.start()
    return thread


# ── HTML Email Templates ───────────────────────────────────────────────────

def _base_template(content_html: str, preview_text: str = "") -> str:
    """Wrap content in the base email shell."""
    year = datetime.now().year
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{PORTAL_NAME}</title>
<style>
  body {{ margin:0; padding:0; background:#f0f4f8; font-family: 'Segoe UI', Helvetica, Arial, sans-serif; }}
  .wrapper {{ max-width:620px; margin:0 auto; background:#ffffff; border-radius:16px; overflow:hidden; box-shadow:0 4px 24px rgba(0,0,0,0.08); margin-top:32px; margin-bottom:32px; }}
  .header {{ background: linear-gradient(135deg, #78350f 0%, #d97706 100%); padding:32px 40px; text-align:center; }}
  .header h1 {{ margin:0; color:#ffffff; font-size:22px; font-weight:800; letter-spacing:0.5px; }}
  .header p {{ margin:6px 0 0; color:rgba(255,255,255,0.85); font-size:13px; }}
  .body {{ padding:36px 40px; }}
  .greeting {{ font-size:18px; font-weight:700; color:#78350f; margin-bottom:8px; }}
  .body p {{ color:#4b5563; line-height:1.7; font-size:15px; margin:0 0 16px; }}
  .info-box {{ background:#fffbeb; border:1px solid #fde68a; border-radius:12px; padding:20px 24px; margin:24px 0; }}
  .info-row {{ display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid #fef3c7; font-size:14px; }}
  .info-row:last-child {{ border-bottom:none; }}
  .info-label {{ color:#92400e; font-weight:600; }}
  .info-value {{ color:#1f2937; font-weight:500; text-align:right; }}
  .cta-btn {{ display:block; width:fit-content; margin:28px auto; background:linear-gradient(135deg, #f59e0b, #d97706); color:#ffffff !important; text-decoration:none; padding:14px 36px; border-radius:50px; font-size:15px; font-weight:700; text-align:center; box-shadow:0 4px 14px rgba(217,119,6,0.35); }}
  .divider {{ border:none; border-top:1px solid #f3f4f6; margin:28px 0; }}
  .footer {{ background:#f9fafb; padding:20px 40px; text-align:center; }}
  .footer p {{ color:#9ca3af; font-size:12px; margin:0; line-height:1.6; }}
  .badge {{ display:inline-block; padding:4px 12px; border-radius:20px; font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px; }}
  .badge-green {{ background:#d1fae5; color:#065f46; }}
  .badge-blue  {{ background:#dbeafe; color:#1e40af; }}
  .badge-amber {{ background:#fef3c7; color:#92400e; }}
  .badge-red   {{ background:#fee2e2; color:#991b1b; }}
</style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <h1>🎓 {PORTAL_NAME}</h1>
    <p>University Name · Training &amp; Placement Cell</p>
  </div>
  <div class="body">
    {content_html}
  </div>
  <div class="footer">
    <p>This email was sent by the University Placement Cell.<br>
    Please do not reply to this email directly.<br>
    &copy; {year} University Name. All rights reserved.</p>
  </div>
</div>
</body>
</html>"""


def build_new_job_email(recipient: dict, company: str, role: str, ctc: str,
                        tier: str, deadline: str, location: str,
                        min_cgpa: float, branches: str) -> str:
    """HTML email for new job posting sent to eligible students."""
    name        = recipient.get('name', 'Student')
    deadline_str = deadline if deadline else 'As announced'
    location_str = location if location else 'Not specified'
    branches_str = branches if branches else 'All branches'

    content = f"""
    <p class="greeting">Hello, {name}! 👋</p>
    <p>Great news! A new placement opportunity has been posted on the <strong>{PORTAL_NAME}</strong> that you are eligible for.</p>
    
    <div class="info-box">
      <div style="margin-bottom:12px;">
        <span style="font-size:20px;font-weight:800;color:#78350f;">{company}</span>
        &nbsp;&nbsp;<span class="badge badge-amber">{tier}</span>
      </div>
      <div class="info-row"><span class="info-label">Role</span><span class="info-value">{role}</span></div>
      <div class="info-row"><span class="info-label">CTC / Package</span><span class="info-value">{ctc} LPA</span></div>
      <div class="info-row"><span class="info-label">Location</span><span class="info-value">{location_str}</span></div>
      <div class="info-row"><span class="info-label">Application Deadline</span><span class="info-value" style="color:#dc2626;font-weight:700;">{deadline_str}</span></div>
      <div class="info-row"><span class="info-label">Min CGPA Required</span><span class="info-value">{min_cgpa}</span></div>
      <div class="info-row"><span class="info-label">Eligible Branches</span><span class="info-value">{branches_str}</span></div>
    </div>

    <p>⚡ <strong>Apply before the deadline expires!</strong> Log in to the portal to review full details and submit your application.</p>

    <a href="{PORTAL_URL}/eligible_companies" class="cta-btn">🚀 View &amp; Apply Now</a>

    <hr class="divider">
    <p style="font-size:13px;color:#6b7280;">You are receiving this email because you are registered on the University Placement Portal and meet the eligibility criteria for this opportunity. If you believe this is an error, please contact the Placement Cell.</p>
    """
    return _base_template(content, f"New Job: {company} – {role}")


def build_status_update_email(recipient: dict, company: str, role: str,
                               status: str, drive_link: str = None) -> str:
    """HTML email for application status update."""
    name = recipient.get('name', 'Student')

    status_badge_class = 'badge-blue'
    status_icon = '📋'
    status_message = f"Your application status for <strong>{company} – {role}</strong> has been updated."

    if status in ('Selected', 'Placed'):
        status_badge_class = 'badge-green'
        status_icon = '🎉'
        status_message = f"Congratulations! You have been <strong>selected by {company}</strong> for the <strong>{role}</strong> position!"
    elif status in ('Not Selected', 'Rejected'):
        status_badge_class = 'badge-red'
        status_icon = '📨'
        status_message = f"Thank you for your effort. Unfortunately, you were not selected for the <strong>{role}</strong> role at <strong>{company}</strong> this time. Keep applying!"
    elif status == 'Shortlisted':
        status_badge_class = 'badge-blue'
        status_icon = '⭐'
        status_message = f"You have been <strong>shortlisted</strong> for the next round at <strong>{company}</strong> for the <strong>{role}</strong> role!"
    elif status == 'Interview Scheduled':
        status_badge_class = 'badge-amber'
        status_icon = '📅'
        status_message = f"Your interview has been <strong>scheduled</strong> with <strong>{company}</strong> for the <strong>{role}</strong> role!"

    drive_section = ""
    if drive_link:
        drive_section = f"""
        <div class="info-box" style="background:#f0f9ff;border-color:#bae6fd;">
          <p style="margin:0;font-size:14px;color:#0c4a6e;font-weight:600;">📎 Interview / Round Link:</p>
          <a href="{drive_link}" style="color:#0369a1;font-size:14px;word-break:break-all;">{drive_link}</a>
        </div>"""

    content = f"""
    <p class="greeting">Hello, {name}! {status_icon}</p>
    <p>{status_message}</p>

    <div class="info-box">
      <div class="info-row"><span class="info-label">Company</span><span class="info-value">{company}</span></div>
      <div class="info-row"><span class="info-label">Role</span><span class="info-value">{role}</span></div>
      <div class="info-row">
        <span class="info-label">Status</span>
        <span class="info-value"><span class="badge {status_badge_class}">{status}</span></span>
      </div>
    </div>

    {drive_section}

    <a href="{PORTAL_URL}/my_applications" class="cta-btn">View My Applications</a>

    <hr class="divider">
    <p style="font-size:13px;color:#6b7280;">Log in to the portal to see full details about your application and upcoming rounds.</p>
    """
    return _base_template(content, f"Application Update: {company} – {status}")


def build_job_update_email(recipient: dict, company: str, role: str,
                           ctc: str, deadline: str, update_note: str = "") -> str:
    """HTML email for job details update."""
    name = recipient.get('name', 'Student')
    deadline_str = deadline if deadline else 'As announced'

    content = f"""
    <p class="greeting">Hello, {name}! 📢</p>
    <p>An update has been made to a job posting on the <strong>{PORTAL_NAME}</strong> that you may have applied to or are eligible for.</p>
    
    <div class="info-box">
      <div style="margin-bottom:12px;">
        <span style="font-size:18px;font-weight:800;color:#78350f;">{company}</span>
      </div>
      <div class="info-row"><span class="info-label">Role</span><span class="info-value">{role}</span></div>
      <div class="info-row"><span class="info-label">Updated Package</span><span class="info-value">{ctc} LPA</span></div>
      <div class="info-row"><span class="info-label">Deadline</span><span class="info-value" style="color:#dc2626;font-weight:700;">{deadline_str}</span></div>
      {f'<div class="info-row"><span class="info-label">Update Note</span><span class="info-value">{update_note}</span></div>' if update_note else ''}
    </div>

    <a href="{PORTAL_URL}/eligible_companies" class="cta-btn">View Updated Job</a>
    """
    return _base_template(content, f"Job Updated: {company} – {role}")


def build_job_cancelled_email(recipient: dict, company: str, role: str) -> str:
    """HTML email when a job is cancelled/removed."""
    name = recipient.get('name', 'Student')
    content = f"""
    <p class="greeting">Hello, {name},</p>
    <p>We regret to inform you that the placement drive for <strong>{company} – {role}</strong> has been <strong>cancelled or removed</strong> from the portal.</p>
    <p>If you had already applied for this position, please note that your application will be considered void.</p>
    <p>We encourage you to check the portal regularly for new opportunities.</p>
    <a href="{PORTAL_URL}/eligible_companies" class="cta-btn">View Other Opportunities</a>
    """
    return _base_template(content, f"Drive Cancelled: {company} – {role}")


def build_announcement_email(recipient: dict, title: str, message: str) -> str:
    """HTML email for general placement announcements."""
    name = recipient.get('name', 'Student')
    content = f"""
    <p class="greeting">Hello, {name}! 📣</p>
    <p>The <strong>University Placement Cell</strong> has an important announcement for you:</p>
    
    <div class="info-box">
      <p style="margin:0 0 8px;font-size:17px;font-weight:800;color:#78350f;">{title}</p>
      <p style="margin:0;color:#4b5563;line-height:1.7;">{message}</p>
    </div>

    <a href="{PORTAL_URL}/eligible_companies" class="cta-btn">Visit Placement Portal</a>
    """
    return _base_template(content, f"Announcement: {title}")
