window.Auth = (() => {
  const key = 'orator_user';
  const getUser = () => { try { return JSON.parse(localStorage.getItem(key)); } catch (_) { return null; } };
  const clearClient = () => { localStorage.removeItem(key); sessionStorage.removeItem(key); if (window.App?.state) { App.state.user = null; App.state.presentations = []; App.state.currentPresentation = null; App.state.currentAttempt = null; App.state.currentRecording = null; } };
  const setUser = user => user ? localStorage.setItem(key, JSON.stringify(user)) : clearClient();
  async function hydrate() { try { const result = await API.me(); if (!result.user) clearClient(); else setUser(result.user); return result.user || null; } catch (_) { clearClient(); return null; } }
  async function login(email, password) { await API.login({ email, password }); const result = await API.me(); if (!result.user) throw new Error('The server did not establish a user session.'); setUser(result.user); return result.user; }
  async function register(name, email, password) { await API.register({ name, email, password }); const result = await API.me(); if (!result.user) throw new Error('The account was created but the session could not be verified.'); setUser(result.user); return result.user; }
  async function logout() {
    try {
      await API.logout();
      const result = await API.me();
      if (result.user) throw new Error('The server session is still active.');
    } catch (error) {
      UI.toast(`Could not sign out: ${error.message}`, true);
      return;
    }
    clearClient();
    location.hash = '#/login';
  }
  return { getUser, setUser, hydrate, login, register, logout, clearClient };
})();
window.AuthViews = (() => {
  function layout(mode) { const register = mode === 'register'; return `<div class="auth-layout"><section class="auth-side"><a class="brand" href="#/"><span class="brand-mark">${icon('waves')}</span>Orator</a><div><div class="eyebrow" style="color:#9dd1bb">Practice with intention</div><h1>Make the next version of your presentation clearer.</h1><p>Turn a rehearsal into useful evidence about your voice, words and presence.</p></div><div class="auth-quote">"The best feedback is specific enough to practice."</div></section><section class="auth-form"><div class="auth-box"><a class="brand" href="#/"><span class="brand-mark">${icon('waves')}</span>Orator</a><h1>${register ? 'Create your account' : 'Welcome back'}</h1><p>${register ? 'Your practice history starts here.' : 'Pick up where your last rehearsal left off.'}</p><form id="auth-form">${register ? `<div class="field"><label for="name">Name</label><input class="input" id="name" required autocomplete="name" placeholder="Your name"></div>` : ''}<div class="field"><label for="email">Email</label><input class="input" id="email" required type="email" autocomplete="email" placeholder="you@example.com"></div><div class="field"><label for="password">Password</label><div class="password-field"><input class="input" id="password" required type="password" minlength="8" autocomplete="${register ? 'new-password' : 'current-password'}" placeholder="At least 8 characters"><button class="btn btn-secondary btn-icon" id="password-toggle" type="button" aria-label="Show password" title="Show password">${icon('eye')}</button></div></div><p id="auth-error" class="form-error" role="alert"></p><button class="btn btn-primary btn-block" type="submit">${register ? 'Create account' : 'Sign in'} ${icon('arrow-right')}</button></form><p class="auth-footer">${register ? 'Already have an account?' : 'New to Orator?'} <a href="#/${register ? 'login' : 'register'}">${register ? 'Sign in' : 'Create an account'}</a></p></div></section></div>`; }
  function bind(mode) { const form = document.getElementById('auth-form'); const password = document.getElementById('password'); const toggle = document.getElementById('password-toggle'); toggle.addEventListener('click', () => { const visible = password.type === 'text'; password.type = visible ? 'password' : 'text'; toggle.setAttribute('aria-label', visible ? 'Show password' : 'Hide password'); toggle.setAttribute('title', visible ? 'Show password' : 'Hide password'); toggle.innerHTML = icon(visible ? 'eye' : 'eye-off'); App.refreshIcons(); }); form.addEventListener('submit', async event => { event.preventDefault(); const error = document.getElementById('auth-error'); const button = form.querySelector('button[type="submit"]'); button.disabled = true; error.textContent = ''; try { if (mode === 'register') await Auth.register(document.getElementById('name').value.trim(), document.getElementById('email').value.trim(), password.value); else await Auth.login(document.getElementById('email').value.trim(), password.value); App.state.user = Auth.getUser(); location.hash = '#/dashboard'; } catch (exception) { error.textContent = exception.message; button.disabled = false; } }); }
  function login() { document.getElementById('app').innerHTML = layout('login'); App.refreshIcons(); bind('login'); }
  function register() { document.getElementById('app').innerHTML = layout('register'); App.refreshIcons(); bind('register'); }
  return { login, register };
})();
