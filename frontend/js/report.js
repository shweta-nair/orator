// Report for ONE stored attempt (#/report/<attempt id>), always read from the database.
// Only metrics that were actually measured are shown - missing ones are left out.
window.ReportView = (() => {
  const { icon, esc, formatDate, formatDuration } = UI;

  const COMPONENT_LABELS = {
    script_accuracy: 'script accuracy', speaking_pace: 'speaking pace', fluency: 'fluency',
    eye_contact: 'eye contact', filler_words: 'filler words'
  };
  const has = value => value !== null && value !== undefined && value !== '';
  const row = (label, value) => `<div class="report-metric"><span>${label}</span><strong>${esc(value)}</strong></div>`;
  const cap = text => text.charAt(0).toUpperCase() + text.slice(1);

  function speechSection(speech) {
    const rows = [];
    if (has(speech.script_accuracy)) rows.push(row('Script accuracy', `${speech.script_accuracy}%`));
    if (has(speech.speaking_pace_wpm)) rows.push(row('Speaking pace', `${speech.speaking_pace_wpm} WPM`));
    if (has(speech.fluency)) rows.push(row('Fluency', speech.fluency));
    if (has(speech.filler_words)) rows.push(row('Filler words', speech.filler_words));

    let body = rows.join('');
    const breakdown = Object.entries(speech.filler_breakdown || {});
    if (speech.filler_words > 0 && breakdown.length) {
      body += `<p class="subtle" style="font-size:11px;margin:15px 0 0">Detected: ${esc(breakdown.map(([word, n]) => `${word} ×${n}`).join(', '))}</p>`;
    }
    if (!rows.length) body = '<p class="subtle" style="font-size:13px;margin:0">No speech was recognised in this recording.</p>';
    return `<section class="card report-section"><h3>${icon('mic-2')} Speech</h3>${body}</section>`;
  }

  function visualSection(visual) {
    const rows = [];
    if (has(visual.eye_contact)) rows.push(row('Eye contact estimate', `${visual.eye_contact}%`));
    if (has(visual.face_detection)) rows.push(row('Face detected', `${visual.face_detection}%`));
    if (has(visual.gesture_activity)) rows.push(row('Gesture activity', cap(String(visual.gesture_activity))));

    let body = rows.join('');
    if (rows.length) {
      const frames = has(visual.frames_analyzed) ? `Based on ${visual.frames_analyzed} sampled video frames. ` : '';
      body += `<p class="subtle" style="font-size:11px;margin:15px 0 0">${frames}Eye contact is an estimate of how often your face was facing the camera; gesture activity reflects movement between frames.</p>`;
    } else {
      body = '<p class="subtle" style="font-size:13px;margin:0">No visual analysis was available for this recording.</p>';
    }
    return `<section class="card report-section"><h3>${icon('scan-face')} Visual</h3>${body}</section>`;
  }

  async function render(state, id) {
    if (!id) return App.navigate('/history');
    const token = App.currentRoute();
    App.shell('history', `<div class="processing"><div class="processing-mark">${icon('loader-circle')}</div><h1>Loading your report...</h1></div>`);

    let attempt;
    try { attempt = await API.attempt(id); }
    catch (error) { if (token === App.currentRoute()) { UI.toast(error.message, true); App.navigate('/history'); } return; }
    if (token !== App.currentRoute()) return;
    state.currentAttempt = attempt;

    const speech = attempt.speech || {};
    const visual = attempt.visual || {};
    const overall = attempt.overall || {};
    const basedOn = (overall.based_on || []).map(key => COMPONENT_LABELS[key] || key);
    const title = attempt.presentation?.title || 'Practice attempt';

    App.shell('history', `
      <div class="report-hero">
        <div><div class="eyebrow">Presentation report</div><h1 style="margin-top:10px">${esc(title)}</h1>
          <p class="subtle" style="margin:9px 0 0">${formatDate(attempt.created_at)} · ${formatDuration(attempt.duration_seconds)}</p></div>
        <div class="report-score"><strong>${has(overall.score) ? esc(overall.score) : '-'}</strong><span>overall score / 100</span></div>
      </div>
      ${basedOn.length ? `<p class="subtle" style="font-size:12px;margin:-10px 0 22px">Score based on: ${esc(basedOn.join(', '))}.</p>` : ''}
      <div class="grid grid-2">${speechSection(speech)}${visualSection(visual)}</div>
      <section class="card report-section" style="margin-top:20px"><h3>${icon('message-circle-more')} Feedback</h3>
        ${(attempt.feedback || []).map(item => `<div class="feedback-item">${esc(item)}</div>`).join('') || '<div class="subtle" style="font-size:13px">No feedback was generated for this attempt.</div>'}
      </section>
      ${attempt.transcript ? `<details class="card report-section" style="margin-top:20px"><summary style="cursor:pointer;font-weight:700">Transcript</summary><p class="subtle" style="font-size:13px;margin:14px 0 0;white-space:pre-wrap">${esc(attempt.transcript)}</p></details>` : ''}
      <div style="margin-top:22px">
        <button class="btn btn-primary" id="practice-again">Practice again ${icon('arrow-right')}</button>
        <a class="btn btn-quiet" href="#/history" style="margin-left:8px">Back to history</a>
      </div>`);

    // Practice again = same presentation, a new attempt.
    document.getElementById('practice-again').addEventListener('click', () => {
      state.currentPresentation = null;
      App.navigate(`/setup/${attempt.presentation_id}`);
    });
  }

  return { render };
})();
