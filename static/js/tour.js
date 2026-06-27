/**
 * ═══════════════════════════════════════════════════════════════
 *  PLACEMENT PORTAL — ONBOARDING TOUR ENGINE  (tour.js)
 *  No external dependencies · Bootstrap 5 compatible
 *  Supports: Student Tour & Admin Tour
 * ═══════════════════════════════════════════════════════════════
 */

class PlacementTour {
  /**
   * @param {Object} config
   * @param {string}   config.tourKey       localStorage key (unique per tour)
   * @param {Array}    config.steps         Array of step objects
   * @param {boolean}  [config.autoStart]   Show welcome modal on first visit
   * @param {string}   [config.theme]       'student' | 'admin'
   */
  constructor(config) {
    this.tourKey   = config.tourKey  || 'placement-tour-done';
    this.steps     = config.steps    || [];
    this.autoStart = config.autoStart !== false;
    this.theme     = config.theme    || 'student';
    this.current   = 0;
    this.active    = false;

    this._spotlight  = null;
    this._card       = null;
    this._overlay    = null;
    this._resizeObs  = null;

    this._buildDOM();
    this._addHelpButton();

    if (this.autoStart && !localStorage.getItem(this.tourKey)) {
      const tryShowWelcome = () => {
        // If there's a Bootstrap modal open (like announcements), wait for it to be dismissed
        if (document.querySelector('.modal.show') || document.querySelector('.modal[style*="display: block"]')) {
          setTimeout(tryShowWelcome, 1000);
        } else {
          this._showWelcome();
        }
      };
      setTimeout(tryShowWelcome, 800);
    }
  }

  /* ── DOM builders ──────────────────────────────────────────── */

  _buildDOM() {
    // Overlay (darkened background)
    this._overlay = document.createElement('div');
    this._overlay.id = 'tour-overlay';
    document.body.appendChild(this._overlay);

    // Spotlight box
    this._spotlight = document.createElement('div');
    this._spotlight.className = 'tour-spotlight';
    this._spotlight.style.display = 'none';
    document.body.appendChild(this._spotlight);

    // Tour card
    this._card = document.createElement('div');
    this._card.className = 'tour-card';
    this._card.style.display = 'none';
    document.body.appendChild(this._card);
  }

  _addHelpButton() {
    const btn = document.createElement('button');
    btn.className = 'tour-help-btn';
    btn.title = 'Help & Tour';
    btn.innerHTML = '❓';
    btn.onclick = () => this._showWelcome(true);
    document.body.appendChild(btn);
  }

  /* ── Welcome Modal ─────────────────────────────────────────── */

  _showWelcome(force = false) {
    if (!force && localStorage.getItem(this.tourKey)) return;

    const isAdmin = this.theme === 'admin';
    const modal = document.createElement('div');
    modal.className = 'tour-welcome-modal';
    modal.id = 'tour-welcome-modal';

    const features = isAdmin
      ? [
          { icon: '📊', text: 'Dashboard statistics at a glance' },
          { icon: '💼', text: 'Post & manage placement drives' },
          { icon: '👥', text: 'View applicants & manage students' },
          { icon: '🎓', text: 'Track student internships & certifications' },
          { icon: '🏠', text: 'Manage homepage updates & announcements' },
          { icon: '📧', text: 'Send email notifications to students' },
          { icon: '📈', text: 'Track placement analytics' },
        ]
      : [
          { icon: '📊', text: 'See your eligibility & applied drives' },
          { icon: '🏢', text: 'Browse eligible companies' },
          { icon: '📄', text: 'Track application status live' },
          { icon: '🎓', text: 'Submit & track your internships' },
          { icon: '🤖', text: 'Analyse your resume with AI' },
          { icon: '🏆', text: 'View your selections & offers' },
        ];

    modal.innerHTML = `
      <div class="tour-welcome-card">
        <div class="tour-welcome-banner">
          <span class="tour-welcome-emoji">🎓</span>
          <h2>Welcome to the Placement Portal!</h2>
          <p>${isAdmin ? 'Manage placements efficiently with a guided walkthrough.' : 'Take a quick tour to get the most out of your portal.'}</p>
        </div>
        <div class="tour-welcome-body">
          <ul>
            ${features.map(f => `<li><span class="icon">${f.icon}</span>${f.text}</li>`).join('')}
          </ul>
          <div class="tour-welcome-actions">
            <button class="btn-start" id="tour-start-btn">
              🚀 Start Tour
            </button>
            <button class="btn-skip-welcome" id="tour-skip-btn">Maybe Later</button>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    document.getElementById('tour-start-btn').onclick = () => {
      localStorage.setItem(this.tourKey, '1');
      modal.remove();
      this.start();
    };
    document.getElementById('tour-skip-btn').onclick = () => {
      localStorage.setItem(this.tourKey, '1');
      modal.remove();
    };
  }

  /* ── Tour lifecycle ────────────────────────────────────────── */

  start(stepIndex = 0) {
    this.current = stepIndex;
    this.active  = true;
    this._overlay.classList.add('active');
    this._overlay.style.display = 'block';
    this._render();

    // Reposition on window resize
    this._resizeObs = new ResizeObserver(() => { if (this.active) this._positionCard(); });
    this._resizeObs.observe(document.body);
    window.addEventListener('resize', () => { if (this.active) this._positionCard(); });
  }

  stop(markDone = true) {
    this.active = false;
    if (markDone) localStorage.setItem(this.tourKey, '1');

    // Remove highlight from current element
    this._clearHighlight();

    // Hide elements
    this._overlay.style.display = 'none';
    this._overlay.classList.remove('active');
    this._spotlight.style.display = 'none';
    this._card.style.display = 'none';

    if (this._resizeObs) this._resizeObs.disconnect();
  }

  next() {
    this._clearHighlight();
    if (this.current < this.steps.length - 1) {
      this.current++;
      this._render();
    } else {
      this._finish();
    }
  }

  prev() {
    this._clearHighlight();
    if (this.current > 0) {
      this.current--;
      this._render();
    }
  }

  _finish() {
    this.stop(true);
    this._showFinishToast();
  }

  /* ── Rendering ─────────────────────────────────────────────── */

  _render() {
    const step = this.steps[this.current];
    if (!step) return;

    // Find the target element
    const el = typeof step.element === 'string'
      ? document.querySelector(step.element)
      : step.element;

    if (!el) {
      // Skip missing elements
      if (this.current < this.steps.length - 1) {
        this.current++;
        this._render();
      } else {
        this._finish();
      }
      return;
    }

    // Check if element is inside a fixed-position ancestor (e.g. sticky header)
    const isFixed = (function checkFixed(node) {
      while (node && node !== document.body) {
        if (window.getComputedStyle(node).position === 'fixed') return true;
        node = node.parentElement;
      }
      return false;
    })(el);

    // Highlight the element
    el.classList.add('tour-target-highlight');
    this._currentEl = el;

    if (isFixed) {
      // Element is fixed — no scroll needed, position immediately
      this._moveSpotlight(el);
      this._buildCard(step, el);
      this._positionCard(el, step.position || 'auto');
    } else {
      // Smooth scroll to element, then update spotlight after scroll settles
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      setTimeout(() => {
        this._moveSpotlight(el);
        this._buildCard(step, el);
        this._positionCard(el, step.position || 'auto');
      }, 400);
    }
  }

  _clearHighlight() {
    if (this._currentEl) {
      this._currentEl.classList.remove('tour-target-highlight');
      this._currentEl = null;
    }
  }

  /* ── Spotlight ─────────────────────────────────────────────── */

  _moveSpotlight(el) {
    const padding = 8;
    const r = el.getBoundingClientRect();
    const s = this._spotlight;
    s.style.display = 'block';
    s.style.top    = `${r.top  - padding}px`;
    s.style.left   = `${r.left - padding}px`;
    s.style.width  = `${r.width  + padding * 2}px`;
    s.style.height = `${r.height + padding * 2}px`;
  }

  /* ── Card ──────────────────────────────────────────────────── */

  _buildCard(step, el) {
    const total   = this.steps.length;
    const current = this.current;
    const isLast  = current === total - 1;

    // Progress dots
    const dots = Array.from({ length: total }, (_, i) => {
      const cls = i < current ? 'done' : i === current ? 'active' : '';
      return `<span class="tour-progress-dot ${cls}"></span>`;
    }).join('');

    this._card.innerHTML = `
      <div class="tour-card-header">
        <div class="tour-card-header-title">
          <div class="tour-card-icon">${step.icon || '👋'}</div>
          <p class="tour-card-step-title">${step.title}</p>
        </div>
        <button class="tour-card-close" id="tour-close-btn" title="Close Tour">✕</button>
      </div>
      <div class="tour-progress-bar-track">
        <div class="tour-progress-bar-fill" style="width:${((current + 1) / total * 100).toFixed(1)}%"></div>
      </div>
      <div class="tour-card-body">
        <div class="tour-card-progress">
          <span>Step ${current + 1} of ${total}</span>
          <div class="tour-progress-dots">${dots}</div>
        </div>
        <p>${step.description}</p>
      </div>
      <div class="tour-card-footer">
        ${current > 0
          ? `<button class="tour-btn tour-btn-secondary" id="tour-prev-btn">← Prev</button>`
          : ''}
        <button class="tour-btn tour-btn-primary" id="tour-next-btn">
          ${isLast ? '🎉 Finish' : 'Next →'}
        </button>
        <button class="tour-btn tour-btn-skip" id="tour-skip-step-btn">Skip Tour</button>
      </div>
    `;

    this._card.style.display = 'block';

    // Bind buttons
    document.getElementById('tour-next-btn').onclick  = () => isLast ? this._finish() : this.next();
    document.getElementById('tour-close-btn').onclick = () => this.stop(false);
    document.getElementById('tour-skip-step-btn').onclick = () => this.stop(true);
    const prevBtn = document.getElementById('tour-prev-btn');
    if (prevBtn) prevBtn.onclick = () => this.prev();
  }

  /* ── Card Positioning ──────────────────────────────────────── */

  _positionCard(el, preferredPos) {
    if (!el) el = this._currentEl;
    if (!el) return;

    const padding = 16;
    const r    = el.getBoundingClientRect();
    const cW   = this._card.offsetWidth  || 320;
    const cH   = this._card.offsetHeight || 220;
    const vW   = window.innerWidth;
    const vH   = window.innerHeight;

    let pos = preferredPos || 'auto';

    // Auto-detect best position
    if (pos === 'auto') {
      const spaceRight  = vW - r.right;
      const spaceLeft   = r.left;
      const spaceBottom = vH - r.bottom;
      const spaceTop    = r.top;

      if (spaceRight >= cW + padding)  pos = 'right';
      else if (spaceLeft >= cW + padding) pos = 'left';
      else if (spaceBottom >= cH + padding) pos = 'bottom';
      else pos = 'top';
    }

    let top, left;

    switch (pos) {
      case 'right':
        top  = Math.min(Math.max(r.top, 10), vH - cH - 10);
        left = r.right + padding;
        break;
      case 'left':
        top  = Math.min(Math.max(r.top, 10), vH - cH - 10);
        left = r.left - cW - padding;
        break;
      case 'bottom':
        top  = r.bottom + padding;
        left = Math.min(Math.max(r.left, 10), vW - cW - 10);
        break;
      case 'top':
        top  = r.top - cH - padding;
        left = Math.min(Math.max(r.left, 10), vW - cW - 10);
        break;
      default:
        // Center of screen fallback
        top  = vH / 2 - cH / 2;
        left = vW / 2 - cW / 2;
        pos  = 'center';
    }

    // Keep card inside viewport
    top  = Math.max(10, Math.min(top,  vH - cH - 10));
    left = Math.max(10, Math.min(left, vW - cW - 10));

    this._card.style.top  = `${top}px`;
    this._card.style.left = `${left}px`;
    this._card.setAttribute('data-pos', pos);
  }

  /* ── Finish toast ──────────────────────────────────────────── */

  _showFinishToast() {
    const t = document.createElement('div');
    t.style.cssText = `
      position:fixed; bottom:30px; left:50%; transform:translateX(-50%) translateY(30px);
      background:linear-gradient(135deg,#10b981,#059669);
      color:#fff; padding:14px 28px; border-radius:40px;
      font-family:'DM Sans',sans-serif; font-size:14px; font-weight:700;
      box-shadow:0 8px 28px rgba(16,185,129,0.4);
      display:flex; align-items:center; gap:10px;
      z-index:9999; transition:all 0.4s cubic-bezier(0.25,1,0.5,1);
    `;
    t.innerHTML = `🎉 Tour complete! You're all set.`;
    document.body.appendChild(t);
    setTimeout(() => { t.style.transform = 'translateX(-50%) translateY(0)'; }, 10);
    setTimeout(() => { t.style.opacity = '0'; t.style.transform = 'translateX(-50%) translateY(20px)'; }, 3000);
    setTimeout(() => t.remove(), 3500);
  }
}

/* ════════════════════════════════════════════════════════════════
   STUDENT TOUR DEFINITION
   ════════════════════════════════════════════════════════════════ */
function initStudentTour() {
  const steps = [
    {
      element:  '[data-tour="dashboard-overview"]',
      title:    'Your Dashboard',
      icon:     '📊',
      position: 'auto',
      description: 'This is your personal placement hub. At a glance, see how many drives you\'re eligible for, how many you\'ve applied to, selections, and your resume strength score.',
    },
    {
      element:  '[data-tour="sidebar-profile"]',
      title:    'Your Profile',
      icon:     '👤',
      position: 'auto',
      description: 'Click here to view and update your profile. Keep your details accurate — CGPA, backlog status, and branch affect your eligibility for placement drives.',
    },
    {
      element:  '[data-tour="sidebar-companies"]',
      title:    'Eligible Companies',
      icon:     '🏢',
      position: 'auto',
      description: 'Browse all placement drives you\'re eligible for. Filter by tier, package, and deadline. Click "Apply" on any drive to submit your application with your resume.',
    },
    {
      element:  '[data-tour="sidebar-internships"]',
      title:    'Internships',
      icon:     '🎓',
      position: 'auto',
      description: 'Submit your internship details here. You can either fill in the official internship form provided by the placement cell or add an external internship you completed. Upload your completion certificate to get it verified.',
    },
    {
      element:  '[data-tour="sidebar-applications"]',
      title:    'Placement History',
      icon:     '📄',
      position: 'auto',
      description: 'Track the real-time status of every application — Pending, Interview, Selected, or Not Selected. Stay updated on where you stand for each drive.',
    },
    {
      element:  '[data-tour="sidebar-selected"]',
      title:    'Selected Companies',
      icon:     '🏆',
      position: 'auto',
      description: 'View the list of companies where you have been successfully placed. Congratulations on your achievements!',
    },
    {
      element:  '[data-tour="resume-analyzer"]',
      title:    'Resume Analyser',
      icon:     '🤖',
      position: 'auto',
      description: 'Upload your resume and select a target job role. Our AI engine scores your resume, highlights matched skills, and shows exactly what\'s missing. Improve your score before applying!',
    },
    {
      element:  '[data-tour="sidebar-logout"]',
      title:    'Logout Safely',
      icon:     '🔒',
      position: 'auto',
      description: 'Always logout when you\'re done, especially on shared computers. Your session is secure and all data is protected. You\'re now ready to explore the portal!',
    },
  ];

  return new PlacementTour({
    tourKey:   'student-tour-done',
    steps:     steps,
    autoStart: true,
    theme:     'student',
  });
}

/* ════════════════════════════════════════════════════════════════
   ADMIN TOUR DEFINITION
   ════════════════════════════════════════════════════════════════ */
function initAdminTour() {
  const steps = [
    {
      element:  '[data-tour="admin-stats"]',
      title:    'Dashboard Overview',
      icon:     '📊',
      position: 'auto',
      description: 'A real-time summary of your batch: total students enrolled, placement rate (based on master sheet selections), active job drives, and average package offered.',
    },
    {
      element:  '[data-tour="admin-master"]',
      title:    'Master Sheet',
      icon:     '📋',
      position: 'auto',
      description: 'Upload the student master sheet (Excel/CSV) here. This is the single source of truth — it populates the student list, eligibility, and selected tier data that drives the placement rate.',
    },
    {
      element:  '[data-tour="admin-jobs"]',
      title:    'Manage Jobs',
      icon:     '💼',
      position: 'auto',
      description: 'Post and manage placement drives by defining eligibility criteria such as CGPA, branch, backlog requirements, tier classification, CTC, and application deadlines. All students can view available opportunities, while the system automatically validates eligibility and allows applications only for drives they qualify for. Administrators can also create reminders with custom messages and schedule a date and time. When the scheduled reminder time is reached, the system automatically sends the reminder message to the faculty registered email address, helping them keep track of important placement-related tasks and deadlines.',
    },
    {
      element:  '[data-tour="admin-applied"]',
      title:    'Applied Students',
      icon:     '👥',
      position: 'auto',
      description: 'View a job-wise breakdown of all students who applied. Download applicant lists as Excel for each company. Use this to share with recruiters.',
    },
    {
      element:  '[data-tour="admin-recruitment"]',
      title:    'Recruitment Process',
      icon:     '🔄',
      position: 'auto',
      description: 'Track multi-round recruitment for each company — set round names, mark pass/fail results per student, and export round-wise data. Keep students informed of their status.',
    },
    {
      element:  '[data-tour="admin-results"]',
      title:    'Job Results Tracker',
      icon:     '📋',
      position: 'auto',
      description: 'View selection and not-selected tables for each available job opening. Get a clear overview of final outcomes per drive.',
    },
    {
      element:  '[data-tour="admin-selected"]',
      title:    'Selected Students',
      icon:     '🏆',
      position: 'auto',
      description: 'View all placed students across all drives. See which tier they were placed in and the company details. This is your final placement outcome report.',
    },
    {
      element:  '[data-tour="admin-analysis"]',
      title:    'Job Analysis',
      icon:     '📈',
      position: 'auto',
      description: 'Compare every job drive side-by-side: how many students applied, got selected, not selected, or are pending — with a colour-coded selection rate bar. Export to XLSX for reports.',
    },
    {
      element:  '[data-tour="admin-internships"]',
      title:    'Internships',
      icon:     '🎓',
      position: 'auto',
      description: 'Post internship form links for students to fill out. View all submitted internship records, verify completion certificates, and export the internship data as an Excel report.',
    },
    {
      element:  '[data-tour="admin-manage-homepage"]',
      title:    'Manage Homepage',
      icon:     '🏠',
      position: 'auto',
      description: 'Control what visitors see on the public-facing homepage. Post updates, achievements, placement statistics, and event announcements that appear on the college portal homepage.',
    },
    {
      element:  '[data-tour="admin-email-manager"]',
      title:    'Email Notifications',
      icon:     '📧',
      position: 'auto',
      description: 'Send targeted emails to students — announce new drives, share round results, or broadcast important messages. Configure your SMTP credentials, view delivery logs, and manage email preferences all from here.',
    },
    {
      element:  '[data-tour="admin-logout"]',
      title:    'All Set! 🎉',
      icon:     '✅',
      position: 'bottom',
      description: 'You\'ve completed the Admin Tour! Remember to logout when done. You can restart this tour any time by clicking the ❓ help button at the bottom-right of the screen.',
    },
  ];

  return new PlacementTour({
    tourKey:   'admin-tour-done',
    steps:     steps,
    autoStart: true,
    theme:     'admin',
  });
}
