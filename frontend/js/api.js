window.API = (() => {
  const base = '/api';

  async function request(path, options = {}) {
    const isFormData = options.body instanceof FormData;
    const opts = {
      credentials: 'include',
      cache: 'no-store',
      ...options,
      headers: {
        ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
        ...(options.headers || {})
      }
    };

    let response;
    try {
      response = await fetch(`${base}${path}`, opts);
    } catch (error) {
      console.error('API connection error:', error);
      throw new Error('The coach could not reach the Flask server. Make sure the backend is running on port 5000.');
    }

    let data = {};
    try {
      data = await response.json();
    } catch (_) {
      data = {};
    }

    if (!response.ok) {
      // Signed-out / expired session on a normal API call (not the login form itself).
      if (response.status === 401 && !path.startsWith('/auth/')) {
        window.Auth?.clearClient();
        location.hash = '#/login';
        throw new Error('Your session has expired. Please log in again.');
      }
      if (response.status === 413) {
        throw new Error('Recording is too large. Please try a shorter recording.');
      }
      const fallback = {
        400: 'Please check the information you entered.',
        401: 'Email or password is incorrect.',
        403: 'You do not have access to that item.',
        404: 'That item could not be found.',
        409: 'That account already exists.',
        422: 'Some information needs attention.',
        500: 'The server had a problem. Check the server logs for details.'
      };
      throw new Error(data.message || fallback[response.status] || `Request failed with status ${response.status}.`);
    }
    return data;
  }

  const post = (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) });

  return {
    base,

    // Authentication
    me: () => request('/auth/me'),
    login: body => post('/auth/login', body),
    register: body => post('/auth/register', body),
    logout: () => request('/auth/logout', { method: 'POST' }),

    // Presentations
    presentations: () => request('/presentations'),
    presentation: id => request(`/presentations/${id}`),
    createPresentation: body => post('/presentations', body),

    // Attempts
    attempts: presentationId => request(`/presentations/${presentationId}/attempts`),
    attempt: id => request(`/attempts/${id}`),

    // One request: the recorded file (camera + microphone) and a small JSON payload.
    submitAttempt: (presentationId, { transcript, durationSeconds, videoBlob }) => {
      const body = new FormData();
      body.append('payload', JSON.stringify({ transcript, duration_seconds: durationSeconds }));
      const extension = (videoBlob.type || '').includes('mp4') ? 'mp4' : 'webm';
      body.append('video', videoBlob, `presentation.${extension}`);
      console.info('[UPLOAD] Sending recording', {
        videoMB: (videoBlob.size / 1024 / 1024).toFixed(2),
        type: videoBlob.type,
        transcriptWords: transcript.trim().split(/\s+/).filter(Boolean).length
      });
      return request(`/presentations/${presentationId}/attempts`, { method: 'POST', body });
    },

    // Pages (all built from the same stored attempts)
    dashboard: () => request('/dashboard'),
    history: () => request('/history'),
    progress: () => request('/progress'),

    health: () => request('/health')
  };
})();
