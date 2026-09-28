// Records camera + microphone into ONE file with MediaRecorder.
// The file is uploaded once; the server samples frames from it itself, so the
// browser never sends frame images or a separate audio file.
window.Recorder = (() => {
  let stream = null;
  let recorder = null;
  let chunks = [];
  let audioContext = null;
  let analyser = null;
  let levelFrame = null;
  let timer = null;
  let startedAt = 0;

  const MIME_CANDIDATES = ['video/webm;codecs=vp8,opus', 'video/webm;codecs=vp9,opus', 'video/webm', 'video/mp4'];
  const supportedMime = () => (window.MediaRecorder ? MIME_CANDIDATES.find(t => MediaRecorder.isTypeSupported(t)) : undefined);

  // 640x480 is plenty for face detection and keeps the upload small.
  const MEDIA_CONSTRAINTS = {
    video: { width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 30 } },
    audio: true
  };

  async function preview(video, onLevel) {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error('Camera and microphone access is not available in this browser.');
    }
    cleanup();
    try {
      stream = await navigator.mediaDevices.getUserMedia(MEDIA_CONSTRAINTS);
    } catch (error) {
      const denied = error && (error.name === 'NotAllowedError' || error.name === 'SecurityError');
      throw new Error(denied
        ? 'Camera and microphone permission was denied. Allow access in your browser and try again.'
        : 'Could not start the camera and microphone. Check that they are connected and not in use elsewhere.');
    }
    video.srcObject = stream;
    setupAudio(onLevel);
    return stream;
  }

  // Start recording (the room page calls this when it opens).
  async function request(video, onLevel, onTime) {
    await preview(video, onLevel);
    if (!window.MediaRecorder) throw new Error('Recording is not supported in this browser. Use a current Chrome or Edge.');
    const mimeType = supportedMime();
    chunks = [];
    recorder = new MediaRecorder(stream, {
      ...(mimeType ? { mimeType } : {}),
      videoBitsPerSecond: 1000000,
      audioBitsPerSecond: 64000
    });
    recorder.ondataavailable = event => { if (event.data && event.data.size) chunks.push(event.data); };
    recorder.start(1000);
    startedAt = performance.now();
    timer = setInterval(() => onTime?.((performance.now() - startedAt) / 1000), 250);
    console.info('[RECORDER] Started', {
      mime: recorder.mimeType,
      audioTracks: stream.getAudioTracks().length,
      videoTracks: stream.getVideoTracks().length
    });
    return stream;
  }

  function setupAudio(onLevel) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass || !stream || !stream.getAudioTracks().length) return;
    audioContext = new AudioContextClass();
    const source = audioContext.createMediaStreamSource(stream);
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);
    const data = new Uint8Array(analyser.frequencyBinCount);
    const draw = () => {
      if (!analyser) return;
      analyser.getByteTimeDomainData(data);
      let sum = 0;
      data.forEach(value => { const sample = (value - 128) / 128; sum += sample * sample; });
      onLevel?.(Math.min(100, Math.round(Math.sqrt(sum / data.length) * 280)));
      levelFrame = requestAnimationFrame(draw);
    };
    draw();
  }

  function stopRecorder() {
    if (!recorder || recorder.state === 'inactive') return Promise.resolve();
    return new Promise(resolve => { recorder.addEventListener('stop', resolve, { once: true }); recorder.stop(); });
  }

  // Stop recording; resolves { videoBlob, duration } (duration = real recording length in seconds).
  async function stop() {
    clearInterval(timer);
    cancelAnimationFrame(levelFrame);
    const duration = startedAt ? (performance.now() - startedAt) / 1000 : 0;
    await stopRecorder();
    const type = recorder?.mimeType || 'video/webm';
    const videoBlob = chunks.length ? new Blob(chunks, { type }) : null;
    console.info('[RECORDER] Stopped', { duration, bytes: videoBlob?.size || 0, type });
    releaseDevices();
    recorder = null;
    chunks = [];
    startedAt = 0;
    return { videoBlob, duration };
  }

  function releaseDevices() {
    stream?.getTracks().forEach(track => track.stop());
    stream = null;
    analyser = null;
    if (audioContext) { audioContext.close().catch(() => {}); audioContext = null; }
  }

  // Release camera + microphone without producing a recording.
  function cleanup() {
    clearInterval(timer);
    cancelAnimationFrame(levelFrame);
    if (recorder && recorder.state !== 'inactive') { try { recorder.stop(); } catch (_) {} }
    recorder = null;
    chunks = [];
    startedAt = 0;
    releaseDevices();
  }

  return { preview, request, stop, cleanup };
})();
