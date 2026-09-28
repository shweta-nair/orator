// Teleprompter: shows the complete script as normal text.
// No sentence/word highlighting and no attempt to follow what is being spoken.
// Controls: start/stop scrolling, scroll speed, reset position. The presenter
// can also scroll the text by hand at any time.
window.Teleprompter = (() => {
  const MIN_SPEED = 10;   // px per second
  const MAX_SPEED = 80;
  const DEFAULT_SPEED = 30;

  let frameId = 0;
  let scrolling = false;
  let lastTime = 0;
  let position = 0;
  let speed = DEFAULT_SPEED;
  let onChange = null;

  function clampSpeed(value) {
    const number = Number(value);
    return Math.max(MIN_SPEED, Math.min(MAX_SPEED, Number.isFinite(number) ? number : DEFAULT_SPEED));
  }

  function render(script) {
    const paragraphs = String(script || '').split(/\n+/).map(line => line.trim()).filter(Boolean);
    if (!paragraphs.length) return '<div class="script-line">Your script will appear here.</div>';
    return paragraphs.map(line => `<div class="script-line">${UI.esc(line)}</div>`).join('');
  }

  function notify() { if (onChange) onChange(scrolling); }

  function tick(timestamp) {
    if (!scrolling) return;
    const box = document.getElementById('script-scroll');
    if (!box) { stop(); return; }
    if (!lastTime) lastTime = timestamp;
    const elapsed = Math.min((timestamp - lastTime) / 1000, 0.1);
    lastTime = timestamp;

    // If the presenter scrolled by hand, continue from where they are.
    if (Math.abs(box.scrollTop - position) > 2) position = box.scrollTop;
    position += speed * elapsed;
    box.scrollTop = position;

    if (box.scrollTop + box.clientHeight >= box.scrollHeight - 1) { stop(); return; }
    frameId = requestAnimationFrame(tick);
  }

  function start() {
    const box = document.getElementById('script-scroll');
    if (!box || scrolling) return;
    scrolling = true;
    lastTime = 0;
    position = box.scrollTop;
    frameId = requestAnimationFrame(tick);
    notify();
  }

  function stop() {
    const was = scrolling;
    scrolling = false;
    if (frameId) cancelAnimationFrame(frameId);
    frameId = 0;
    lastTime = 0;
    if (was) notify();
  }

  function toggle() { scrolling ? stop() : start(); return scrolling; }

  function reset() {
    const box = document.getElementById('script-scroll');
    if (box) box.scrollTop = 0;
    position = 0;
    lastTime = 0;
  }

  function setSpeed(value) { speed = clampSpeed(value); return speed; }

  // Called when leaving the practice room.
  function destroy() { stop(); onChange = null; }
  function setListener(callback) { onChange = callback; }

  return { render, start, stop, toggle, reset, setSpeed, destroy, setListener,
           isScrolling: () => scrolling, MIN_SPEED, MAX_SPEED, DEFAULT_SPEED };
})();
