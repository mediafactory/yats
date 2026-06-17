/*
 * YATS shared frontend helpers (vanilla + Alpine).
 * Replaces the old jQuery-based AJAX/CSRF handling.
 */
(function () {
  'use strict';

  // ---- CSRF ----
  function getCookie(name) {
    const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return m ? decodeURIComponent(m.pop()) : '';
  }
  const csrftoken = getCookie('csrftoken');

  // fetch wrapper that always sends the CSRF header for unsafe methods.
  async function request(url, opts = {}) {
    const method = (opts.method || 'GET').toUpperCase();
    const headers = Object.assign(
      { 'X-Requested-With': 'XMLHttpRequest' },
      opts.headers || {}
    );
    if (!['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method)) {
      headers['X-CSRFToken'] = csrftoken;
    }
    const resp = await fetch(url, Object.assign({ credentials: 'same-origin' }, opts, { headers }));
    return resp;
  }

  // Convenience: POST form-encoded data (mirrors old jQuery $.post defaults).
  function post(url, data) {
    const body = new URLSearchParams(data || {});
    return request(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8' },
      body,
    });
  }

  const YATS = { getCookie, csrftoken, request, post };
  window.YATS = YATS;

  // ---- Theme (light/dark) ----
  // Applied as early as possible (this script is in <head>, before <body>
  // paints) so there's no flash of the wrong theme. Default: OS preference,
  // overridable and persisted in localStorage.
  function preferredTheme() {
    var saved = localStorage.getItem('yats.theme');
    if (saved === 'light' || saved === 'dark') return saved;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark' : 'light';
  }
  function applyTheme(theme) {
    document.documentElement.classList.toggle('dark', theme === 'dark');
  }
  applyTheme(preferredTheme());
  YATS.preferredTheme = preferredTheme;
  YATS.applyTheme = applyTheme;

  // ---- Alpine global store (sidebar + modal state) ----
  // Registered before Alpine initialises so x-data/$store work everywhere.
  document.addEventListener('alpine:init', () => {
    const store = {
      // sidebar
      sidebarOpen: false,            // mobile drawer
      collapsed: localStorage.getItem('yats.sidebar.collapsed') === '1',
      toggleSidebar() { this.sidebarOpen = !this.sidebarOpen; },
      toggleCollapsed() {
        this.collapsed = !this.collapsed;
        localStorage.setItem('yats.sidebar.collapsed', this.collapsed ? '1' : '0');
      },
      // modals: keyed by id, open the one whose id matches
      modal: null,
      openModal(id) { this.modal = id; this.sidebarOpen = false; },
      closeModal() { this.modal = null; },
      // upload progress (0-100), bound by the ticket-view Dropzone
      uploadProgress: 0,
      // theme
      theme: YATS.preferredTheme(),
      toggleTheme() {
        this.theme = this.theme === 'dark' ? 'light' : 'dark';
        localStorage.setItem('yats.theme', this.theme);
        YATS.applyTheme(this.theme);
      },
    };
    window.Alpine.store('ui', store);
  });
})();
