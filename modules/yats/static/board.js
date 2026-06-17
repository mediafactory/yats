/*
 * Kanban / board drag-and-drop and layout (vanilla, replaces the jQuery version).
 * Shared by board/view.html and board/kanban.html.
 * Globals supplied by the page: edges, finish_state, all_states, ticketid,
 * list_items, plus the helper functions move()/loadTicketData() (kanban only).
 */
(function () {
  function sizeColumns() {
    var cols = document.querySelectorAll('.panel-body');
    cols.forEach(function (c) { c.style.maxHeight = (window.innerHeight - 150) + 'px'; });
    var container = document.querySelector('.container-fluid');
    if (container) container.style.minWidth = (cols.length * 350) + 'px';
  }

  document.addEventListener('DOMContentLoaded', function () {
    sizeColumns();
    draggableInit();
  });
  window.addEventListener('resize', sizeColumns);

  function draggableInit() {
    var sourceId;

    document.querySelectorAll('[draggable=true]').forEach(function (el) {
      el.addEventListener('dragstart', function (event) {
        sourceId = el.parentNode.getAttribute('id');
        var node = event.target;
        while (node.nodeName !== 'ARTICLE') { node = node.parentNode; }
        event.dataTransfer.setData('text/plain', node.getAttribute('id'));
      });
    });

    document.querySelectorAll('.panel-body').forEach(function (body) {
      body.addEventListener('dragover', function (event) { event.preventDefault(); });

      body.addEventListener('drop', function (event) {
        event.preventDefault();
        // the inner .kanban-centered div carries the list id; tickets get
        // prepended back into it on close/reassign/move.
        var listDiv = body.querySelector('[id^="list"]') || body.firstElementChild;
        var targetId = listDiv ? listDiv.getAttribute('id') : null;
        if (!targetId) return;

        var elementId = event.dataTransfer.getData('text/plain');
        var availListIDs = window.edges[sourceId.replace('list', '')];
        var newListID = parseInt(targetId.replace('list', ''));

        if (availListIDs && availListIDs.indexOf(newListID) > -1) {
          if (sourceId && sourceId !== targetId) {
            window.ticketid = parseInt(elementId.replace('item', ''));
            var new_state = parseInt(targetId.replace('list', ''));
            window.list_items = listDiv;

            if (new_state === window.finish_state) {
              if (window.Alpine) window.Alpine.store('ui').openModal('closeDlg');
            } else if (event.ctrlKey || event.altKey || event.metaKey) {
              if (window.Alpine) window.Alpine.store('ui').openModal('processing-modal');
              window.move(window.ticketid, new_state);
            } else {
              var sel = document.getElementById('id_state');
              if (sel) {
                if (!window.all_states) {
                  window.all_states = Array.prototype.map.call(sel.options, function (o) {
                    return { value: o.value, text: o.text };
                  });
                }
                sel.innerHTML = '';
                window.all_states.forEach(function (o) {
                  if (parseInt(o.value) === newListID) {
                    var opt = document.createElement('option');
                    opt.value = o.value; opt.text = o.text;
                    sel.appendChild(opt);
                  }
                });
              }
              if (window.loadTicketData) window.loadTicketData();
              if (window.Alpine) window.Alpine.store('ui').openModal('reassignDlg');
            }
          }
        } else {
          showalert('State not allowed for ticket #' + elementId.replace('item', ''), 'alert-error');
        }
      });
    });
  }

  function showalert(message, alerttype) {
    var ph = document.getElementById('alert_placeholder');
    if (!ph) { alert(message); return; }
    var div = document.createElement('div');
    div.id = 'alertdiv';
    div.className = 'alert ' + alerttype + ' mb-2';
    div.innerHTML = '<span>' + message + '</span>';
    ph.appendChild(div);
    setTimeout(function () { if (div.parentNode) div.parentNode.removeChild(div); }, 5000);
  }

  window.draggableInit = draggableInit;
  window.showalert = showalert;
})();
