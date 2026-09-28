// Application shell, router, landing page and settings.
window.App = (() => {
  const { icon, esc, toast, refreshIcons, formatDate, formatDuration } = UI;
  const state = { user: null, currentPresentation: null, currentAttempt: null, currentRecording: null };
  const app = document.getElementById('app');
  let routeCounter = 0;

  const navigate = path => { location.hash = path; };
  // Views call this after every `await`; a newer navigation makes the older render stop.
  const currentRoute = () => routeCounter;

  // ------------------------------------------------------------------ shell
  function shell(active, content, title = '') {
    const user = state.user;
    const initials = (user?.name || 'You').split(' ').map(x => x[0]).join('').slice(0, 2).toUpperCase();
    const collapsed = localStorage.getItem('orator_sidebar') === 'collapsed';
    const link = (key, href, label, iconName) =>
      `<a class="nav-link ${active === key ? 'active' : ''}" data-tooltip="${label}" href="${href}">${icon(iconName)}<span>${label}</span></a>`;

    app.innerHTML = `<div class="app-layout ${collapsed ? 'sidebar-collapsed' : ''}">
      <aside class="sidebar" aria-label="Application sidebar">
        <button class="sidebar-toggle" data-action="sidebar-toggle" aria-label="${collapsed ? 'Expand' : 'Collapse'} sidebar" title="${collapsed ? 'Expand' : 'Collapse'} sidebar">${icon(collapsed ? 'chevron-right' : 'chevron-left')}</button>
        <a class="brand" href="#/dashboard"><span class="brand-mark">${icon('waves')}</span><span>Orator</span></a>
        <nav class="nav" aria-label="Main navigation">
          ${link('dashboard', '#/dashboard', 'Overview', 'layout-dashboard')}
          ${link('history', '#/history', 'History', 'clock-3')}
          ${link('progress', '#/progress', 'Progress', 'trending-up')}
          ${link('settings', '#/settings', 'Settings', 'settings-2')}
        </nav>
        <div class="sidebar-bottom">
          <div class="user-chip"><span class="avatar">${esc(initials)}</span><div><strong>${esc(user?.name || 'Guest')}</strong><span>${esc(user?.email || 'Not signed in')}</span></div></div>
          <button class="btn btn-quiet btn-block" data-action="logout" data-tooltip="Sign out">${icon('log-out')}<span>Sign out</span></button>
        </div>
      </aside>
      <div class="sidebar-backdrop" data-action="close-sidebar"></div>
      <div class="main-column main-content">
        <header class="topbar">
          <button class="btn btn-secondary btn-icon mobile-menu-toggle" data-action="open-sidebar" aria-label="Open sidebar" title="Open sidebar">${icon('menu')}</button>
          <a class="brand" href="#/dashboard"><span class="brand-mark">${icon('waves')}</span>Orator</a>
          <div class="top-actions"><span class="subtle" style="font-size:12px">${esc(title)}</span><button class="btn btn-secondary btn-icon" data-action="theme" aria-label="Toggle theme">${icon('sun-moon')}</button></div>
        </header>
        <main class="page-content">${content}</main>
      </div></div>`;

    const layout = app.querySelector('.app-layout');
    app.querySelector('[data-action="sidebar-toggle"]')?.addEventListener('click', () => {
      const next = !layout.classList.contains('sidebar-collapsed');
      layout.classList.toggle('sidebar-collapsed', next);
      localStorage.setItem('orator_sidebar', next ? 'collapsed' : 'expanded');
      const button = app.querySelector('[data-action="sidebar-toggle"]');
      button.setAttribute('aria-label', next ? 'Expand sidebar' : 'Collapse sidebar');
      button.setAttribute('title', next ? 'Expand sidebar' : 'Collapse sidebar');
      button.innerHTML = icon(next ? 'chevron-right' : 'chevron-left');
      refreshIcons();
    });
    app.querySelector('[data-action="open-sidebar"]')?.addEventListener('click', () => layout.classList.add('mobile-sidebar-open'));
    app.querySelector('[data-action="close-sidebar"]')?.addEventListener('click', () => layout.classList.remove('mobile-sidebar-open'));
    app.querySelectorAll('.nav-link').forEach(l => l.addEventListener('click', () => layout.classList.remove('mobile-sidebar-open')));
    app.querySelector('[data-action="logout"]')?.addEventListener('click', Auth.logout);
    app.querySelectorAll('[data-action="theme"]').forEach(button => button.addEventListener('click', toggleTheme));
    refreshIcons();
  }

  function toggleTheme() {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    localStorage.setItem('orator_theme', next);
  }

  // ---------------------------------------------------------------- landing
  function landing() {
    app.innerHTML = `<header class="topbar"><a class="brand" href="#/"><span class="brand-mark">${icon('waves')}</span>Orator</a><div class="top-actions"><a class="btn btn-quiet" href="#/login">Sign in</a><a class="btn btn-primary" href="#/register">Start practicing ${icon('arrow-up-right')}</a></div></header>
    <main><section class="hero-grid"><div class="hero-copy"><div class="eyebrow">AI presentation coach</div><h1 class="display-title" style="margin-top:15px">Practice presentations with a coach that shows you what happened.</h1><p>Record a rehearsal and get feedback on your script accuracy, speaking pace, fluency, filler words, eye contact and gestures.</p><div class="hero-actions"><a class="btn btn-primary" href="#/register">Start practicing ${icon('arrow-right')}</a><a class="btn btn-secondary" href="#how-it-works">See how it works</a></div></div>
    <div class="signal-visual" aria-label="Speech and video are analysed and combined into feedback"><div class="signal-orbit"></div><div class="signal-center">${icon('sparkles')}</div><div class="signal-card speech">${icon('mic-2')}<strong>Speech</strong><span>Accuracy, pace, fluency, fillers</span></div><div class="signal-card video">${icon('video')}<strong>Video</strong><span>Eye contact, gestures</span></div><div class="signal-card model">${icon('brain-circuit')}<strong>Feedback</strong><span>Combined into a score, grounded in your attempt</span></div></div></section>
    <section id="how-it-works" class="feature-section alt"><div class="eyebrow">A calmer way to improve</div><h2 style="margin-top:12px">One focused rehearsal. A clearer next step.</h2>
    <div class="feature-list"><article class="feature-item">${icon('file-pen-line')}<h3>Bring your words</h3><p>Paste a script, choose a scenario and set a target before you begin.</p></article><article class="feature-item">${icon('scan-face')}<h3>Practice naturally</h3><p>Read from the teleprompter while your camera and microphone capture the session.</p></article><article class="feature-item">${icon('chart-no-axes-combined')}<h3>See what changed</h3><p>Review your report, then practice again and watch your progress.</p></article></div>
    <div class="scenario-list"><span class="scenario">Academic</span><span class="scenario">News reporter</span><span class="scenario">Flight attendant</span><span class="scenario">Advertisement</span><span class="scenario">Formal speech</span><span class="scenario">Public speaking</span></div></section></main>`;
    refreshIcons();
  }

  // --------------------------------------------------------------- settings
  function settings() {
    const speed = Number(localStorage.getItem('orator_speed')) || Teleprompter.DEFAULT_SPEED;
    shell('settings', `<div class="page-heading"><div><div class="eyebrow">Preferences</div><h1 style="margin-top:9px">Settings</h1><p>Keep it simple.</p></div></div>
      <div class="grid grid-2">
        <section class="card card-pad"><div class="section-title"><h2>Profile</h2>${icon('user-round')}</div><div class="form-grid"><div class="field"><label>Name</label><input class="input" value="${esc(state.user?.name)}" disabled></div><div class="field"><label>Email</label><input class="input" value="${esc(state.user?.email)}" disabled></div></div></section>
        <section class="card card-pad"><div class="section-title"><h2>Teleprompter</h2>${icon('type')}</div><div class="field"><label for="pref-speed">Default scroll speed (${Teleprompter.MIN_SPEED}-${Teleprompter.MAX_SPEED} px/s)</label><input id="pref-speed" class="input" type="number" min="${Teleprompter.MIN_SPEED}" max="${Teleprompter.MAX_SPEED}" value="${speed}"></div><button class="btn btn-primary" style="margin-top:18px" data-save-prefs>Save</button></section>
        <section class="card card-pad"><div class="section-title"><h2>Appearance</h2>${icon('palette')}</div><button class="btn btn-secondary" data-action="theme">${icon('sun-moon')} Toggle light / dark mode</button></section>
      </div>`);
    document.querySelector('[data-save-prefs]')?.addEventListener('click', () => {
      const value = Teleprompter.setSpeed(document.getElementById('pref-speed').value);
      localStorage.setItem('orator_speed', value);
      document.getElementById('pref-speed').value = value;
      toast('Teleprompter speed saved.');
    });
  }

  // ----------------------------------------------------------------- router
  async function route() {
    routeCounter += 1;
    PresentationView.leave();   // release camera/microphone if the practice room is being left

    const [path, param] = (location.hash.slice(1) || '/').split('/').filter(Boolean);
    const authPages = ['login', 'register'];
    if (!state.user && path && !authPages.includes(path)) return navigate('/login');
    if (state.user && (!path || authPages.includes(path))) return navigate('/dashboard');

    switch (path) {
      case undefined: return landing();
      case 'login': return AuthViews.login();
      case 'register': return AuthViews.register();
      case 'dashboard': return DashboardView.render(state);
      case 'history': return DashboardView.history(state);
      case 'progress': return ProgressView.render(state);
      case 'settings': return settings();
      case 'create': return PresentationView.create(state);
      case 'setup': return PresentationView.setup(state, param);
      case 'room': return PresentationView.room(state, param);
      case 'processing': return PresentationView.processing(state);
      case 'report': return ReportView.render(state, param);
      default: return navigate('/dashboard');
    }
  }

  async function init() {
    const theme = localStorage.getItem('orator_theme');
    if (theme) document.documentElement.dataset.theme = theme;
    state.user = await Auth.hydrate();
    window.addEventListener('hashchange', route);
    await route();
  }

  return { state, init, shell, toast, navigate, currentRoute, esc, formatDate, formatDuration, refreshIcons };
})();
window.addEventListener('DOMContentLoaded', App.init);
