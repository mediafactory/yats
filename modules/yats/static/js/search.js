/*
 * Full-text search typeahead (Alpine component).
 * Replaces the old Bloodhound/typeahead.js + Handlebars setup.
 *
 * The /search/auto/ endpoint returns a bare JSON array and behaves differently
 * per query (mirrors the original three Bloodhound sources):
 *   ?suggestions=1&models=...   -> [{caption}]            (spelling suggestion)
 *   ?models=web.test            -> [{id, caption, closed}] (tickets)
 *   ?models=yats.docs           -> [{id, caption}]         (documents)
 */
document.addEventListener('alpine:init', () => {
  window.Alpine.data('fulltextSearch', () => ({
    q: new URLSearchParams(location.search).get('q') || '',
    open: false,
    loading: 0,
    suggestions: [],
    tickets: [],
    docs: [],
    _t: null,

    onInput() {
      clearTimeout(this._t);
      const term = this.q.trim();
      if (term.length < 2) { this.reset(); return; }
      this._t = setTimeout(() => this.fetchAll(term), 200);
    },

    reset() {
      this.suggestions = []; this.tickets = []; this.docs = [];
      this.open = false;
    },

    async one(params) {
      this.loading++;
      try {
        const resp = await window.YATS.request('/search/auto/?' + params);
        return await resp.json();
      } catch (e) {
        return [];
      } finally {
        this.loading--;
      }
    },

    async fetchAll(term) {
      const enc = encodeURIComponent(term);
      const [sug, tics, docs] = await Promise.all([
        this.one('suggestions=1&models=web.test&models=yats.docs&q=' + enc),
        this.one('models=web.test&q=' + enc),
        this.one('models=yats.docs&q=' + enc),
      ]);
      this.suggestions = sug || [];
      this.tickets = tics || [];
      this.docs = docs || [];
      this.open = this.suggestions.length || this.tickets.length || this.docs.length;
    },

    useSuggestion(s) {
      this.q = (s.caption || '').trim();
      this.onInput();
      this.$refs.input.focus();
    },

    submit() {
      if (this.q.trim()) { this.$refs.form.submit(); }
    },
  }));
});
