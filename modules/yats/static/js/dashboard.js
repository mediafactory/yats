/*
 * Dashboard (Alpine component + Chart.js).
 *
 * The server renders every widget once, in default order. This component owns
 * the per-user view state (order + visibility), persists it to
 * /dashboard/config/ via YATS.post, and draws the charts from the JSON the
 * server embedded. Reordering uses the native HTML5 drag & drop API (same
 * approach as board.js); no jQuery.
 */
document.addEventListener('alpine:init', () => {
  window.Alpine.data('dashboard', (config, chartData) => ({
    config: config || [],          // [{id, visible}], the canonical order
    chartData: chartData || {},
    labels: {},
    dragId: null,
    _charts: [],

    init() {
      const el = document.getElementById('dash-labels');
      if (el) {
        try { this.labels = JSON.parse(el.textContent); } catch (e) { this.labels = {}; }
      }
      // charts need the canvases laid out first
      this.$nextTick(() => this.drawCharts());
    },

    // ---- order / visibility ----
    orderIndex(id) {
      const i = this.config.findIndex((w) => w.id === id);
      return i < 0 ? 999 : i;
    },
    orderStyle(id) {
      return 'order:' + this.orderIndex(id);
    },
    isVisible(id) {
      const w = this.config.find((x) => x.id === id);
      return w ? w.visible : true;
    },

    // ---- drag & drop reordering ----
    onDragStart(ev, id) {
      this.dragId = id;
      ev.dataTransfer.effectAllowed = 'move';
    },
    onDrop(ev, targetId) {
      ev.preventDefault();
      const from = this.dragId;
      if (!from || from === targetId) return;
      const fromIdx = this.orderIndex(from);
      const toIdx = this.orderIndex(targetId);
      const moved = this.config.splice(fromIdx, 1)[0];
      this.config.splice(toIdx, 0, moved);
      this.dragId = null;
      this.save();
    },

    // ---- persistence ----
    async save() {
      try {
        await window.YATS.request('/dashboard/config/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.config),
        });
      } catch (e) { /* non-fatal: state stays in the DOM until reload */ }
      this.$store.ui.closeModal();
    },

    // ---- charts ----
    drawCharts() {
      this._charts.forEach((c) => c.destroy());
      this._charts = [];
      const palette = ['#0088cc', '#5bc0de', '#5cb85c', '#f0ad4e', '#d9534f',
                       '#9b59b6', '#34495e', '#1abc9c', '#e67e22', '#7f8c8d'];

      document.querySelectorAll('canvas[data-chart]').forEach((canvas) => {
        const key = canvas.getAttribute('data-chart');
        const type = canvas.getAttribute('data-chart-type') || 'doughnut';
        const d = this.chartData[key];
        if (!d || !d.labels || !d.labels.length) return;
        const isBar = type === 'bar';
        const chart = new window.Chart(canvas, {
          type,
          data: {
            labels: d.labels,
            datasets: [{
              data: d.data,
              backgroundColor: isBar ? '#0088cc' : d.labels.map((_, i) => palette[i % palette.length]),
            }],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: !isBar, position: 'bottom' } },
            scales: isBar ? { y: { beginAtZero: true, ticks: { precision: 0 } } } : {},
          },
        });
        this._charts.push(chart);
      });
    },
  }));
});
