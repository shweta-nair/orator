// Dashboard overview + History. Both read the database through /api/dashboard and /api/history.
window.DashboardView = (() => {
  const { icon, esc, formatDate, formatDuration, formatScore } = UI;

  function greeting() {
    const hour = new Date().getHours();
    return hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
  }

  const emptyState = `<div class="empty-state"><div class="empty-icon">${icon('sparkles')}</div><strong>No presentation data yet.</strong><p>Start a practice session to make your first entry.</p><a class="btn btn-primary" href="#/create">Create a presentation</a></div>`;

  function metricCards(data) {
    const latest = data.latest_score;
    return `<div class="grid grid-4" style="margin-bottom:22px">
      <div class="card metric-card"><div class="metric-top"><span>Latest score</span><span class="metric-icon">${icon('gauge')}</span></div><div class="metric-value" id="stat-latest">${latest != null ? `${latest}/100` : 'Not available'}</div><div class="metric-note">From your most recent attempt</div></div>
      <div class="card metric-card"><div class="metric-top"><span>Practice sessions</span><span class="metric-icon">${icon('repeat-2')}</span></div><div class="metric-value" id="stat-sessions">${data.practice_sessions}</div><div class="metric-note">Completed attempts</div></div>
      <div class="card metric-card"><div class="metric-top"><span>Presentations</span><span class="metric-icon">${icon('files')}</span></div><div class="metric-value" id="stat-presentations">${data.presentation_count}</div><div class="metric-note">Scripts ready to rehearse</div></div>
      <div class="card metric-card"><div class="metric-top"><span>Analysis</span><span class="metric-icon">${icon('activity')}</span></div><div class="metric-value" style="font-size:19px">${data.analysis_ready ? 'Analysis ready' : 'Setup needed'}</div><div class="metric-note">${data.analysis_ready ? 'Speech and video analysis available' : 'The face detector could not be loaded'}</div></div>
    </div>`;
  }

  function recentTable(recent) {
    if (!recent.length) return emptyState;
    return `<div class="table-wrap"><table class="data-table"><thead><tr><th>Presentation</th><th>Scenario</th><th>Date</th><th>Duration</th><th>Score</th></tr></thead><tbody>
      ${recent.map(a => `<tr data-href="#/report/${a.id}"><td><strong>${esc(a.presentation_title)}</strong></td><td>${esc(a.scenario)}</td><td>${formatDate(a.created_at)}</td><td>${formatDuration(a.duration_seconds)}</td><td><span class="badge">${a.overall_score}/100</span></td></tr>`).join('')}
    </tbody></table></div>`;
  }

  function bindRows() {
    document.querySelectorAll('tr[data-href]').forEach(rowEl => rowEl.addEventListener('click', () => { location.hash = rowEl.dataset.href; }));
  }

  async function render(state) {
    const token = App.currentRoute();
    let data;
    try { data = await API.dashboard(); }
    catch (error) { UI.toast(error.message, true); data = { presentation_count: 0, practice_sessions: 0, latest_score: null, recent: [], analysis_ready: false }; }
    if (token !== App.currentRoute()) return;

    const first = esc(state.user?.name?.split(' ')[0] || 'there');
    App.shell('dashboard', `
      <div class="page-heading"><div><div class="eyebrow">Your practice space</div><h1 style="margin-top:9px">${greeting()}, ${first}</h1><p>Ready for your next practice?</p></div><a class="btn btn-primary" href="#/create">${icon('plus')} New presentation</a></div>
      ${metricCards(data)}
      <div class="card"><div class="card-pad section-title"><div><h2>Recent activity</h2><p class="subtle" style="margin:5px 0 0;font-size:12px">Your latest practice sessions</p></div><a href="#/history" class="btn btn-quiet">View all ${icon('arrow-up-right')}</a></div>${recentTable(data.recent || [])}</div>`);
    bindRows();
  }

  // -------------------------------------------------------------- history
  function attemptRow(attempt, label) {
    return `<div class="report-metric"><span>${label} · ${formatDate(attempt.created_at)} · ${formatDuration(attempt.duration_seconds)}</span><span><strong>${formatScore(attempt.overall_score)}</strong> <a class="btn btn-quiet" href="#/report/${attempt.id}" style="min-height:32px">View report</a></span></div>`;
  }

  function presentationCard(p) {
    const attempts = p.attempts || [];              // newest first
    const latest = attempts[0];
    const previous = attempts.slice(1);
    return `<article class="card card-pad history-item" style="margin:0 20px 16px">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap">
        <div><h3 style="font-size:17px">${esc(p.title)}</h3><p class="subtle" style="margin:6px 0 0;font-size:12px"><span style="text-transform:capitalize">${esc(p.scenario)}</span> · ${attempts.length} attempt${attempts.length === 1 ? '' : 's'}</p></div>
        <button class="btn btn-secondary" data-practice="${p.id}">${icon('rotate-ccw')} ${attempts.length ? 'Practice again' : 'Practice'}</button>
      </div>
      ${latest ? `<div style="margin-top:14px">${attemptRow(latest, 'Latest attempt')}</div>` : '<p class="subtle" style="font-size:13px;margin:14px 0 0">No attempts yet.</p>'}
      ${previous.length ? `<details style="margin-top:8px"><summary class="subtle" style="cursor:pointer;font-size:12px">Previous attempts (${previous.length})</summary>${previous.map((a, i) => attemptRow(a, `Attempt ${previous.length - i}`)).join('')}</details>` : ''}
    </article>`;
  }

  async function history(state) {
    const token = App.currentRoute();
    let items = [];
    try { items = (await API.history()).presentations; }
    catch (error) { UI.toast(error.message, true); }
    if (token !== App.currentRoute()) return;

    App.shell('history', `
      <div class="page-heading"><div><div class="eyebrow">Your archive</div><h1 style="margin-top:9px">Presentation history</h1><p>Every attempt is a useful data point.</p></div><a class="btn btn-primary" href="#/create">${icon('plus')} New presentation</a></div>
      <div class="card">${items.length ? `<div class="card-pad"><div class="field" style="max-width:320px"><label for="history-filter">Filter presentations</label><input id="history-filter" class="input" placeholder="Search by title or scenario"></div></div>
        <div id="history-list" style="padding-bottom:4px">${items.map(presentationCard).join('')}</div>
        <div id="history-none" class="empty-state" style="display:none"><strong>No matching presentations.</strong></div>` : emptyState}</div>`);

    document.querySelectorAll('[data-practice]').forEach(button => button.addEventListener('click', () => {
      state.currentPresentation = null;
      App.navigate(`/setup/${button.dataset.practice}`);
    }));
    const filter = document.getElementById('history-filter');
    filter?.addEventListener('input', () => {
      const query = filter.value.trim().toLowerCase();
      let visible = 0;
      document.querySelectorAll('#history-list .history-item').forEach(card => {
        const match = card.textContent.toLowerCase().includes(query);
        card.style.display = match ? '' : 'none';
        if (match) visible += 1;
      });
      document.getElementById('history-none').style.display = visible ? 'none' : '';
    });
  }

  return { render, history };
})();
