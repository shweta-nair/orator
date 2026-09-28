// Progress page: statistics and charts built from the stored attempts (/api/progress).
window.ProgressView = (() => {
  const { icon, esc, formatDate, formatDuration } = UI;

  const stat = (label, value) => `<div class="card metric-card"><div class="metric-top"><span>${label}</span></div><div class="metric-value">${esc(value)}</div></div>`;

  function statCards(data) {
    const cards = [
      stat('Sessions completed', data.sessions),
      stat('Average score', data.average_score),
      stat('Latest score', data.latest_score),
      stat('Best score', data.best_score)
    ];
    if (data.average_script_accuracy != null) cards.push(stat('Avg script accuracy', `${data.average_script_accuracy}%`));
    if (data.average_speaking_pace_wpm != null) cards.push(stat('Avg speaking pace', `${data.average_speaking_pace_wpm} WPM`));
    if (data.average_eye_contact != null) cards.push(stat('Avg eye contact', `${data.average_eye_contact}%`));
    if (data.average_fluency != null) cards.push(stat('Avg fluency', data.average_fluency));
    return `<div class="grid grid-4" style="margin-bottom:22px">${cards.join('')}</div>`;
  }

  function attemptsTable(attempts) {
    return `<div class="card" style="margin-top:20px"><div class="card-pad section-title"><h2>Attempts</h2></div><div class="table-wrap"><table class="data-table" id="progress-table"><thead><tr><th>#</th><th>Presentation</th><th>Date</th><th>Duration</th><th>Score</th></tr></thead><tbody>
      ${attempts.map(a => `<tr data-href="#/report/${a.id}"><td>${a.attempt_number}</td><td><strong>${esc(a.presentation_title)}</strong></td><td>${formatDate(a.created_at)}</td><td>${formatDuration(a.duration_seconds)}</td><td><span class="badge">${a.overall_score}/100</span></td></tr>`).join('')}
    </tbody></table></div></div>`;
  }

  function drawCharts(attempts) {
    if (!window.Chart) {
      document.querySelectorAll('.chart-box').forEach(box => { box.innerHTML = '<p class="subtle" style="font-size:13px">The chart library could not be loaded (it needs an internet connection). Your attempts are listed in the table below.</p>'; });
      return;
    }
    const labels = attempts.map(a => `Attempt ${a.attempt_number}`);
    const options = extra => ({
      responsive: true, maintainAspectRatio: false,
      scales: { y: { min: 0, max: 100, grid: { color: '#e2e5dc' } }, x: { grid: { display: false } } },
      plugins: { legend: { display: !!extra } }
    });
    const line = (label, values, color) => ({ label, data: values, borderColor: color, backgroundColor: color, tension: .3, spanGaps: true, pointRadius: 4 });

    new Chart(document.getElementById('score-chart'), {
      type: 'line',
      data: { labels, datasets: [line('Overall score', attempts.map(a => a.overall_score), '#176b5b')] },
      options: options(false)
    });
    new Chart(document.getElementById('trend-chart'), {
      type: 'line',
      data: { labels, datasets: [
        line('Script accuracy', attempts.map(a => a.script_accuracy ?? null), '#176b5b'),
        line('Fluency', attempts.map(a => a.fluency ?? null), '#e4a24a'),
        line('Eye contact', attempts.map(a => a.eye_contact ?? null), '#5b7fbf')
      ] },
      options: options(true)
    });
  }

  async function render() {
    const token = App.currentRoute();
    let data = null;
    try { data = await API.progress(); }
    catch (error) { UI.toast(error.message, true); }
    if (token !== App.currentRoute()) return;

    const attempts = data?.attempts || [];
    App.shell('progress', `
      <div class="page-heading"><div><div class="eyebrow">Long view</div><h1 style="margin-top:9px">Progress analytics</h1><p>Patterns become useful when you can see them over time.</p></div></div>
      ${attempts.length ? `${statCards(data)}
        <div class="grid grid-2">
          <section class="card"><div class="card-pad section-title"><h2>Score over attempts</h2><span class="badge">${attempts.length} attempt${attempts.length === 1 ? '' : 's'}</span></div><div class="chart-box"><canvas id="score-chart"></canvas></div></section>
          <section class="card"><div class="card-pad section-title"><h2>Metric trends</h2></div><div class="chart-box"><canvas id="trend-chart"></canvas></div></section>
        </div>${attemptsTable(attempts)}`
      : `<div class="card empty-state"><div class="empty-icon">${icon('trending-up')}</div><h2>Complete your first presentation to start tracking progress.</h2><p>Your scores will appear here after an analysed attempt.</p><a class="btn btn-primary" href="#/create">Start a practice</a></div>`}`);

    if (attempts.length) {
      drawCharts(attempts);
      document.querySelectorAll('tr[data-href]').forEach(rowEl => rowEl.addEventListener('click', () => { location.hash = rowEl.dataset.href; }));
    }
  }

  return { render };
})();
