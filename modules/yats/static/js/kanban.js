/*
 * Kanban-specific behaviour (vanilla, replaces jQuery + BootstrapMenu).
 * Provides the snooze context menu on the clock icons and the
 * sleep/close/reassign/move/seen/ignore/loadTicketData actions.
 *
 * The page sets window.kanbanLabels (translated strings) and the globals
 * finish_state / edges before loading this file.
 */
(function () {
  'use strict';

  // ---- simple context menu ----
  function buildMenu(items) {
    var menu = document.createElement('div');
    menu.className = 'fixed z-[80] bg-white border border-gray-200 rounded shadow-lg py-1 text-sm hidden';
    items.forEach(function (it) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'block w-full text-left px-4 py-1 hover:bg-gray-100';
      b.textContent = it.name;
      b.addEventListener('click', function () {
        hide();
        it.onClick(menu._targetId);
      });
      menu.appendChild(b);
    });
    document.body.appendChild(menu);

    function hide() { menu.classList.add('hidden'); }
    menu._hide = hide;
    document.addEventListener('click', function (e) {
      if (!menu.contains(e.target)) hide();
    });
    return menu;
  }

  function attachMenu(selector, items) {
    var menu = buildMenu(items);
    document.querySelectorAll(selector).forEach(function (el) {
      el.addEventListener('click', function (e) {
        e.stopPropagation();
        menu._targetId = el.getAttribute('id');
        menu.style.left = e.clientX + 'px';
        menu.style.top = e.clientY + 'px';
        menu.classList.remove('hidden');
      });
    });
  }

  function reinsert(ticketid) {
    var element = document.getElementById('item' + ticketid);
    if (element && window.list_items) window.list_items.prepend(element);
  }

  window.kanbanInit = function (labels) {
    var dayItems = [
      { d: '1', name: '1 ' + labels.day }, { d: '2', name: '2 ' + labels.day },
      { d: '3', name: '3 ' + labels.day }, { d: '4', name: '4 ' + labels.day },
      { d: '5', name: '5 ' + labels.day }, { d: '6', name: '6 ' + labels.day },
      { d: '7', name: '1 ' + labels.week }, { d: '14', name: '2 ' + labels.week },
      { d: '21', name: '3 ' + labels.week }, { d: '30', name: labels.month },
    ].map(function (x) {
      return { name: x.name, onClick: function (id) { sleep(id, x.d); } };
    });
    attachMenu('.fa-clock-o', dayItems);
  };

  function sleep(elementId, interval) {
    var ticket = elementId.substr(1);
    YATS.request('/tickets/sleep/' + ticket + '/?interval=' + interval).then(function () {
      var el = document.getElementById('item' + ticket);
      if (el) el.remove();
    });
  }

  window.close = function () {
    var form = document.querySelector('#closeDlg form');
    if (!document.getElementById('id_resolution').value || !document.getElementById('id_close_comment').value) {
      alert(window.kanbanLabels.fillRequired);
      return;
    }
    YATS.post('/tickets/view/' + window.ticketid + '/', new URLSearchParams(new FormData(form))).then(function () {
      reinsert(window.ticketid);
      if (window.Alpine) window.Alpine.store('ui').closeModal();
    });
  };

  window.loadTicketData = function () {
    YATS.request('/tickets/json/' + window.ticketid + '/').then(function (r) { return r.json(); }).then(function (data) {
      var a = document.getElementById('id_assigned'); if (a) a.value = data.assigned;
      var p = document.getElementById('id_priority'); if (p) p.value = data.priority;
    });
  };

  window.reassign = function () {
    var form = document.querySelector('#reassignDlg form');
    if (!document.getElementById('id_assigned').value || !document.getElementById('id_reassign_comment').value) {
      alert(window.kanbanLabels.fillRequired);
      return;
    }
    YATS.post('/tickets/reassign/' + window.ticketid + '/', new URLSearchParams(new FormData(form))).then(function () {
      reinsert(window.ticketid);
      if (window.Alpine) window.Alpine.store('ui').closeModal();
    });
  };

  window.move = function (ticketid, state) {
    YATS.post('/tickets/move/' + ticketid + '/', { simple: '1', state: state }).then(function () {
      reinsert(ticketid);
      if (window.Alpine) window.Alpine.store('ui').closeModal();
    });
  };

  window.seen = function (ticket) {
    if (confirm(window.kanbanLabels.confirmRemove)) {
      YATS.request('/tickets/notify/' + ticket + '/').then(function () {
        var el = document.getElementById('item' + ticket); if (el) el.remove();
      });
    }
  };

  window.ignore = function (ticket) {
    if (confirm(window.kanbanLabels.confirmRemove)) {
      YATS.request('/tickets/ignore/' + ticket + '/').then(function () {
        var el = document.getElementById('item' + ticket); if (el) el.remove();
      });
    }
  };
})();
