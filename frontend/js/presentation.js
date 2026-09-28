// Create presentation -> device setup -> practice room (teleprompter + recording) -> upload/analysis.
window.PresentationView = (() => {
  const { icon, esc } = UI;
  const SCENARIOS = [
    ['academic', 'Academic presentation'], ['news', 'News reporter'], ['flight', 'Flight attendant'],
    ['advertisement', 'Advertisement'], ['speech', 'Formal speech'], ['general', 'Public speaking']
  ];
  let activeRoom = null;   // speech recognition of the open practice room, if any

  async function ensurePresentation(state, id) {
    if (state.currentPresentation && String(state.currentPresentation.id) === String(id)) return state.currentPresentation;
    state.currentPresentation = await API.presentation(id);
    return state.currentPresentation;
  }

  // ---------------------------------------------------------------- create
  function create(state) {
    App.shell('dashboard', `
      <div class="page-heading"><div><div class="eyebrow">New rehearsal</div><h1 style="margin-top:9px">Shape the practice.</h1><p>Start with the words you want to make more natural.</p></div></div>
      <div class="card card-pad" style="max-width:900px">
        <form id="create-form" class="form-grid">
          <div class="field field-full"><label for="presentation-title">Presentation title</label><input id="presentation-title" class="input" required placeholder="e.g. Q3 product story"></div>
          <div class="field"><label for="scenario">Scenario</label><select id="scenario" class="select">${SCENARIOS.map(([value, label]) => `<option value="${value}">${label}</option>`).join('')}</select></div>
          <div class="field"><label for="difficulty">Difficulty</label><select id="difficulty" class="select"><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></select></div>
          <div class="field field-full"><label for="script">Script</label><textarea id="script" class="textarea" required placeholder="Paste or write your script here..."></textarea>
            <div style="display:flex;justify-content:space-between;gap:12px"><span class="subtle" style="font-size:11px">Plain text is enough. The full script is shown in the teleprompter.</span><label class="btn btn-secondary" style="min-height:32px;font-size:11px">${icon('upload')} Upload text<input id="script-file" type="file" accept=".txt,text/plain" hidden></label></div></div>
          <div class="field"><label for="target">Target duration (optional)</label><input id="target" class="input" type="number" min="0.5" step="0.5" placeholder="Minutes"></div>
          <div class="field" style="justify-content:flex-end"><button class="btn btn-primary" type="submit">Continue to setup ${icon('arrow-right')}</button></div>
        </form>
      </div>`);

    const file = document.getElementById('script-file');
    file.addEventListener('change', () => {
      if (!file.files[0]) return;
      const reader = new FileReader();
      reader.onload = () => { document.getElementById('script').value = reader.result; };
      reader.readAsText(file.files[0]);
    });
    document.getElementById('create-form').addEventListener('submit', async event => {
      event.preventDefault();
      const target = document.getElementById('target').value;
      const body = {
        title: document.getElementById('presentation-title').value.trim(),
        scenario: document.getElementById('scenario').value,
        difficulty: document.getElementById('difficulty').value,
        script: document.getElementById('script').value.trim(),
        target_duration_minutes: target === '' ? null : Number(target)
      };
      try {
        state.currentPresentation = await API.createPresentation(body);
        App.navigate(`/setup/${state.currentPresentation.id}`);
      } catch (error) { UI.toast(error.message, true); }
    });
  }

  // ----------------------------------------------------------------- setup
  async function setup(state, id) {
    const token = App.currentRoute();
    let presentation;
    try { presentation = await ensurePresentation(state, id); }
    catch (error) { UI.toast(error.message, true); return App.navigate('/dashboard'); }
    if (token !== App.currentRoute()) return;

    App.shell('dashboard', `
      <div class="page-heading"><div><div class="eyebrow">Before you begin</div><h1 style="margin-top:9px">Set up your room.</h1><p>${esc(presentation.title)} · ${esc(presentation.scenario)}</p></div></div>
      <div class="grid grid-2">
        <section class="card card-pad"><div class="section-title"><h2>Camera preview</h2><span id="camera-status" class="badge badge-neutral">Not connected</span></div>
          <div class="setup-video" style="aspect-ratio:16/10;overflow:hidden;border-radius:14px;background:#17241f"><video id="setup-video" autoplay muted playsinline style="width:100%;height:100%;object-fit:cover;transform:scaleX(-1)"></video></div>
          <button id="permission-btn" class="btn btn-primary" style="margin-top:18px">${icon('camera')} Check camera and microphone</button>
          <p id="permission-note" class="subtle" style="font-size:12px;margin-bottom:0">Your devices stay local until you submit an attempt.</p></section>
        <section class="card card-pad"><div class="section-title"><h2>Ready to practice?</h2>${icon('shield-check')}</div>
          <div class="stack" style="gap:13px">
            <div class="setup-check"><span class="status-dot"></span><div><strong>Camera</strong><p id="camera-check">Waiting for permission</p></div></div>
            <div class="setup-check"><span class="status-dot"></span><div><strong>Microphone</strong><p id="mic-check">Waiting for permission</p></div></div>
            <div class="audio-preview"><div style="display:flex;justify-content:space-between"><strong>Microphone level</strong><span id="setup-level">0%</span></div><div class="progress-track"><div id="setup-level-bar" class="progress-fill" style="width:0%"></div></div></div>
          </div>
          <button id="start-practice" class="btn btn-primary btn-block" style="margin-top:28px" disabled>Start practice ${icon('arrow-right')}</button></section>
      </div>`);

    const permission = document.getElementById('permission-btn');
    permission.addEventListener('click', async () => {
      try {
        await Recorder.preview(document.getElementById('setup-video'), level => {
          const readout = document.getElementById('setup-level');
          if (readout) readout.textContent = `${level}%`;
          const bar = document.getElementById('setup-level-bar');
          if (bar) bar.style.width = `${level}%`;
        });
        Recorder.cleanup();
        document.getElementById('camera-status').textContent = 'Ready';
        document.getElementById('camera-status').className = 'badge';
        document.getElementById('camera-check').textContent = 'Camera ready';
        document.getElementById('mic-check').textContent = 'Microphone ready';
        document.getElementById('start-practice').disabled = false;
        permission.textContent = 'Devices checked';
      } catch (error) {
        document.getElementById('permission-note').textContent = error.message;
        UI.toast(error.message, true);
      }
    });
    document.getElementById('start-practice').addEventListener('click', () => App.navigate(`/room/${presentation.id}`));
  }

  // ------------------------------------------------------------------ room
  function stopRecognition(recognition) {
    if (!recognition) return Promise.resolve();
    recognition.stopped = true;
    if (!recognition.running) return Promise.resolve();
    return new Promise(resolve => {
      const timer = setTimeout(resolve, 1500);   // let the recogniser deliver its last words
      recognition.addEventListener('end', () => { clearTimeout(timer); resolve(); }, { once: true });
      try { recognition.stop(); } catch (_) { clearTimeout(timer); resolve(); }
    });
  }

  function createRecognition(getTranscript, appendTranscript) {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      UI.toast('This browser has no speech recognition, so only visual metrics can be analysed. Use Chrome or Edge for the full analysis.', true);
      return null;
    }
    const recognition = new SR();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'en-US';
    recognition.running = false;
    recognition.stopped = false;
    recognition.onstart = () => { recognition.running = true; };
    recognition.onresult = event => {
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        if (event.results[i].isFinal) appendTranscript(`${event.results[i][0].transcript} `);
      }
    };
    recognition.onerror = event => {
      if (['not-allowed', 'service-not-allowed', 'network'].includes(event.error)) {
        recognition.stopped = true;   // do not keep retrying
        UI.toast(event.error === 'network'
          ? 'Speech recognition could not reach its online service, so the transcript may be empty.'
          : 'Speech recognition is blocked in this browser, so the transcript may be empty.', true);
      }
    };
    recognition.onend = () => {
      recognition.running = false;
      if (!recognition.stopped) { try { recognition.start(); } catch (_) {} }
    };
    return recognition;
  }

  async function room(state, id) {
    const token = App.currentRoute();
    let presentation;
    try { presentation = await ensurePresentation(state, id); }
    catch (error) { UI.toast(error.message, true); return App.navigate('/dashboard'); }
    if (token !== App.currentRoute()) return;

    const savedSpeed = Number(localStorage.getItem('orator_speed')) || Teleprompter.DEFAULT_SPEED;
    App.shell('dashboard', `
      <div class="page-heading"><div><div class="eyebrow">${esc(presentation.scenario)}</div><h1 style="margin-top:9px">${esc(presentation.title)}</h1></div><span class="badge">${icon('lock-keyhole')} Private practice</span></div>
      <div class="room-layout">
        <section class="room-card"><div class="room-stage">
          <video id="room-video" autoplay muted playsinline></video>
          <div class="room-meta"><span class="live-badge"><i></i> RECORDING</span><span id="room-timer" class="timer">00:00</span></div>
          <div class="room-script"><div id="script-scroll" class="script-scroll">${Teleprompter.render(presentation.script)}</div></div>
          <div class="camera-mini"><video id="mini-video" autoplay muted playsinline></video></div>
          <div class="room-controls">
            <button class="btn" id="scroll-toggle">${icon('play')} Start scrolling</button>
            <label>Speed <input id="room-speed" type="range" min="${Teleprompter.MIN_SPEED}" max="${Teleprompter.MAX_SPEED}" step="1" value="${savedSpeed}"> <output id="speed-value">${savedSpeed} px/s</output></label>
            <button class="btn" id="reset-scroll">${icon('rotate-ccw')} Reset</button>
            <button class="btn finish" id="finish-room">Finish practice ${icon('check')}</button>
          </div></div></section>
        <aside class="live-panel"><div class="card card-pad">
          <div class="section-title"><h2>Recording</h2>${icon('activity')}</div>
          <div class="live-metric"><header><span>Microphone</span><strong id="live-level">0%</strong></header><div class="progress-track"><div id="live-level-bar" class="progress-fill" style="width:0%"></div></div></div>
          <p class="subtle" style="font-size:12px;margin:14px 0 0">Read your script at your own pace - scroll it yourself or use the scrolling controls. Your metrics are calculated after you finish.</p>
        </div></aside>
      </div>`);

    const video = document.getElementById('room-video');
    const mini = document.getElementById('mini-video');
    let transcript = '';
    const recognition = createRecognition(() => transcript, text => { transcript += text; });
    activeRoom = { recognition };

    try {
      const stream = await Recorder.request(
        video,
        level => {
          const readout = document.getElementById('live-level');
          if (readout) readout.textContent = `${level}%`;
          const bar = document.getElementById('live-level-bar');
          if (bar) bar.style.width = `${level}%`;
        },
        seconds => {
          const timer = document.getElementById('room-timer');
          if (timer) timer.textContent = `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`;
        });
      if (token !== App.currentRoute()) { Recorder.cleanup(); return; }
      mini.srcObject = stream;
      if (recognition) { try { recognition.start(); } catch (_) {} }
    } catch (error) {
      if (token !== App.currentRoute()) return;
      UI.toast(error.message, true);
      return App.navigate(`/setup/${presentation.id}`);
    }

    // Teleprompter controls: start/stop scrolling, speed, reset. Nothing else.
    Teleprompter.setSpeed(savedSpeed);
    const toggle = document.getElementById('scroll-toggle');
    Teleprompter.setListener(scrolling => {
      toggle.innerHTML = scrolling ? `${icon('pause')} Stop scrolling` : `${icon('play')} Start scrolling`;
      UI.refreshIcons();
    });
    toggle.addEventListener('click', () => Teleprompter.toggle());
    document.getElementById('room-speed').addEventListener('input', event => {
      const value = Teleprompter.setSpeed(event.target.value);
      document.getElementById('speed-value').textContent = `${value} px/s`;
    });
    document.getElementById('reset-scroll').addEventListener('click', () => Teleprompter.reset());

    document.getElementById('finish-room').addEventListener('click', async event => {
      event.currentTarget.disabled = true;
      Teleprompter.destroy();
      const [recorded] = await Promise.all([Recorder.stop(), stopRecognition(recognition)]);
      activeRoom = null;
      if (!recorded.videoBlob || !recorded.videoBlob.size) {
        UI.toast('The recording was empty and could not be submitted. Please try again.', true);
        return App.navigate(`/setup/${presentation.id}`);
      }
      state.currentRecording = { videoBlob: recorded.videoBlob, duration: recorded.duration, transcript: transcript.trim() };
      App.navigate('/processing');
    });
  }

  // ------------------------------------------------------------ processing
  function processing(state) {
    const recording = state.currentRecording;
    const presentation = state.currentPresentation;
    if (!recording?.videoBlob || !presentation) return App.navigate('/dashboard');

    App.shell('dashboard', `<div class="processing"><div class="processing-mark">${icon('sparkles')}</div><div class="eyebrow">One moment</div><h1 style="margin-top:11px">Analyzing your presentation...</h1>
      <p id="processing-status" class="subtle" style="margin:12px auto 0;max-width:480px">Uploading your recording and analysing speech and video.</p>
      <div class="stage-list"><div class="stage-item active">${icon('loader-circle')} Uploading and analysing (this can take a little while for longer recordings)</div></div>
      <div id="processing-actions" style="margin-top:20px"></div></div>`);

    let submitting = false;
    const submit = async () => {
      if (submitting) return;
      submitting = true;
      document.getElementById('processing-actions').innerHTML = '';
      document.getElementById('processing-status').textContent = 'Uploading your recording and analysing speech and video.';
      try {
        const attempt = await API.submitAttempt(presentation.id, {
          transcript: recording.transcript,
          durationSeconds: recording.duration,
          videoBlob: recording.videoBlob
        });
        state.currentRecording = null;
        App.navigate(`/report/${attempt.id}`);
      } catch (error) {
        submitting = false;
        const status = document.getElementById('processing-status');
        if (!status) return;   // user already left this page
        status.textContent = error.message;
        UI.toast(error.message, true);
        document.getElementById('processing-actions').innerHTML =
          `<button class="btn btn-primary" id="retry-upload">Try again</button> <a class="btn btn-quiet" href="#/dashboard">Discard recording</a>`;
        document.getElementById('retry-upload').addEventListener('click', submit);
      }
    };
    submit();
  }

  // Called by the router whenever the page changes: release camera/microphone
  // and stop the teleprompter if the practice room is being left.
  function leave() {
    Teleprompter.destroy();
    Recorder.cleanup();
    if (activeRoom?.recognition) { activeRoom.recognition.stopped = true; try { activeRoom.recognition.abort(); } catch (_) {} }
    activeRoom = null;
  }

  return { create, setup, room, processing, leave };
})();
