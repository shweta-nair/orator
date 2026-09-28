// Small helpers shared by every view.
window.UI = (() => {
  const icon = name => `<i data-lucide="${name}" class="icon" aria-hidden="true"></i>`;

  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));

  function toast(message, isError = false) {
    const node = document.createElement('div');
    node.className = `toast${isError ? ' error' : ''}`;
    node.textContent = message;
    document.getElementById('toast-region').appendChild(node);
    setTimeout(() => node.remove(), 4200);
  }

  const refreshIcons = () => window.lucide?.createIcons();

  const formatDate = date => date
    ? new Date(date).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
    : 'Not available';

  function formatDuration(seconds) {
    if (seconds == null) return 'Not available';
    const total = Math.round(Number(seconds));
    return `${Math.floor(total / 60)}m ${String(total % 60).padStart(2, '0')}s`;
  }

  const formatScore = score => (score == null ? 'Not available' : `${score}/100`);

  return { icon, esc, toast, refreshIcons, formatDate, formatDuration, formatScore };
})();

// Used by the auth views.
window.icon = UI.icon;
