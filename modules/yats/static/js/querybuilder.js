/*
 * Lightweight query builder (vanilla JS), replacing jQuery QueryBuilder.
 * Produces the exact {condition, rules:[...]} tree consumed by
 * yats/shortcuts.py createQuery(). Operators map 1:1 to the backend names.
 *
 * Mount: a #builder div, plus <script type="application/json" id="qb-filters">
 * (array of filter metadata) and optional #qb-rules (a previously saved tree).
 */
(function () {
  'use strict';

  var OP_LABELS = {
    equal: '=', not_equal: '!=', less: '<', less_or_equal: '<=',
    greater: '>', greater_or_equal: '>=', between: 'between', not_between: 'not between',
    is_null: 'is null', is_not_null: 'is not null',
    is_empty: 'is empty', is_not_empty: 'is not empty',
    begins_with: 'begins with', not_begins_with: "doesn't begin with",
    contains: 'contains', not_contains: "doesn't contain",
    ends_with: 'ends with', not_ends_with: "doesn't end with",
  };
  var NO_VALUE = ['is_null', 'is_not_null', 'is_empty', 'is_not_empty'];
  var TWO_VALUE = ['between', 'not_between'];

  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }

  function QueryBuilder(root, filters, rules) {
    this.root = root;
    this.filters = filters;
    this.byId = {};
    filters.forEach(function (f) { this.byId[f.id] = f; }, this);
    this.container = el('div');
    root.appendChild(this.container);
    this.tree = this.renderGroup(rules || { condition: 'AND', rules: [] });
    this.container.appendChild(this.tree.node);
  }

  // ---- Group ----
  QueryBuilder.prototype.renderGroup = function (data) {
    var self = this;
    var node = el('div', 'qb-group border border-gray-300 rounded-md p-3 mb-2 bg-gray-50');
    var head = el('div', 'flex items-center gap-2 mb-2');

    var cond = el('div', 'inline-flex rounded overflow-hidden border border-gray-300 text-sm');
    var condState = { value: data.condition || 'AND' };
    ['AND', 'OR'].forEach(function (c) {
      var b = el('button', 'px-3 py-1', c);
      b.type = 'button';
      function paint() {
        b.className = 'px-3 py-1 ' + (condState.value === c ? 'bg-brand text-white' : 'bg-white text-gray-600');
      }
      b.addEventListener('click', function () { condState.value = c; cond.querySelectorAll('button').forEach(function (x) { x._paint(); }); });
      b._paint = paint; paint();
      cond.appendChild(b);
    });
    head.appendChild(cond);

    var addRule = el('button', 'btn btn-default btn-small', '+ rule'); addRule.type = 'button';
    var addGroup = el('button', 'btn btn-default btn-small', '+ group'); addGroup.type = 'button';
    head.appendChild(addRule); head.appendChild(addGroup);

    var del = el('button', 'btn btn-danger btn-small ml-auto', '×'); del.type = 'button';
    head.appendChild(del);
    node.appendChild(head);

    var body = el('div', 'qb-body pl-2');
    node.appendChild(body);

    var children = [];
    var group = { node: node, condState: condState, children: children, isGroup: true };

    del.addEventListener('click', function () {
      if (group._parent) group._parent.removeChild(group);
    });
    addRule.addEventListener('click', function () {
      var r = self.renderRule({});
      r._parent = group; children.push(r); body.appendChild(r.node);
    });
    addGroup.addEventListener('click', function () {
      var g = self.renderGroup({ condition: 'AND', rules: [] });
      g._parent = group; children.push(g); body.appendChild(g.node);
    });
    group.removeChild = function (child) {
      var i = children.indexOf(child);
      if (i > -1) { children.splice(i, 1); body.removeChild(child.node); }
    };

    (data.rules || []).forEach(function (rd) {
      var child = ('rules' in rd) ? self.renderGroup(rd) : self.renderRule(rd);
      child._parent = group; children.push(child); body.appendChild(child.node);
    });

    return group;
  };

  // ---- Rule ----
  QueryBuilder.prototype.renderRule = function (data) {
    var self = this;
    var node = el('div', 'qb-rule flex flex-wrap items-center gap-2 mb-2 p-2 bg-white border border-gray-200 rounded');

    var fieldSel = el('select', 'no-base form-control !w-auto');
    this.filters.forEach(function (f) {
      var o = el('option', null, f.label); o.value = f.id; fieldSel.appendChild(o);
    });
    var opSel = el('select', 'no-base form-control !w-auto');
    var valWrap = el('span', 'inline-flex items-center gap-1');

    var del = el('button', 'btn btn-danger btn-small ml-auto', '×'); del.type = 'button';

    node.appendChild(fieldSel);
    node.appendChild(opSel);
    node.appendChild(valWrap);
    node.appendChild(del);

    var rule = { node: node, fieldSel: fieldSel, opSel: opSel, valWrap: valWrap, isGroup: false };

    function buildOps() {
      var f = self.byId[fieldSel.value];
      opSel.innerHTML = '';
      (f.operators || ['equal']).forEach(function (op) {
        var o = el('option', null, OP_LABELS[op] || op); o.value = op; opSel.appendChild(o);
      });
    }
    function buildValue() {
      var f = self.byId[fieldSel.value];
      var op = opSel.value;
      valWrap.innerHTML = '';
      if (NO_VALUE.indexOf(op) > -1) return;
      var count = TWO_VALUE.indexOf(op) > -1 ? 2 : 1;
      for (var i = 0; i < count; i++) {
        valWrap.appendChild(self.valueInput(f));
        if (i === 0 && count === 2) valWrap.appendChild(document.createTextNode(' … '));
      }
    }

    fieldSel.addEventListener('change', function () { buildOps(); buildValue(); });
    opSel.addEventListener('change', buildValue);
    del.addEventListener('click', function () { if (rule._parent) rule._parent.removeChild(rule); });

    // initialise from saved data
    if (data.id) fieldSel.value = data.id;
    buildOps();
    if (data.operator) opSel.value = data.operator;
    buildValue();
    if (data.value != null) {
      var inputs = valWrap.querySelectorAll('input,select');
      var vals = Array.isArray(data.value) ? data.value : [data.value];
      inputs.forEach(function (inp, i) { if (vals[i] != null) inp.value = vals[i]; });
    }

    return rule;
  };

  QueryBuilder.prototype.valueInput = function (f) {
    var input;
    if (f.input === 'select') {
      input = el('select', 'no-base form-control !w-auto');
      (f.values || []).forEach(function (v) {
        var o = el('option', null, v.label); o.value = v.value; input.appendChild(o);
      });
    } else if (f.input === 'radio') {
      input = el('select', 'no-base form-control !w-auto');
      (f.values || []).forEach(function (v) {
        var o = el('option', null, v.label); o.value = v.value; input.appendChild(o);
      });
    } else {
      input = el('input', 'no-base form-control !w-auto');
      input.type = f.input === 'number' ? 'number'
        : f.input === 'date' ? 'date'
        : f.input === 'datetime' ? 'datetime-local'
        : 'text';
    }
    return input;
  };

  // ---- Serialise ----
  QueryBuilder.prototype.collectGroup = function (group) {
    var rules = [];
    group.children.forEach(function (child) {
      if (child.isGroup) {
        var g = this.collectGroup(child);
        if (g.rules.length) rules.push(g);
      } else {
        var r = this.collectRule(child);
        if (r) rules.push(r);
      }
    }, this);
    return { condition: group.condState.value, rules: rules };
  };

  QueryBuilder.prototype.collectRule = function (rule) {
    var f = this.byId[rule.fieldSel.value];
    var op = rule.opSel.value;
    var out = { id: rule.fieldSel.value, operator: op };
    if (NO_VALUE.indexOf(op) === -1) {
      var inputs = rule.valWrap.querySelectorAll('input,select');
      var vals = [];
      inputs.forEach(function (i) { vals.push(i.value); });
      out.value = (TWO_VALUE.indexOf(op) > -1) ? vals : (vals[0] != null ? vals[0] : '');
    }
    return out;
  };

  QueryBuilder.prototype.getRules = function () {
    return this.collectGroup(this.tree);
  };

  QueryBuilder.prototype.reset = function () {
    this.container.removeChild(this.tree.node);
    this.tree = this.renderGroup({ condition: 'AND', rules: [] });
    this.container.appendChild(this.tree.node);
  };

  // ---- Mount ----
  document.addEventListener('DOMContentLoaded', function () {
    var mount = document.getElementById('builder');
    if (!mount) return;
    var filtersEl = document.getElementById('qb-filters');
    if (!filtersEl) return;
    var filters = JSON.parse(filtersEl.textContent);
    var rulesEl = document.getElementById('qb-rules');
    var rules = rulesEl ? JSON.parse(rulesEl.textContent) : null;
    window.yatsQueryBuilder = new QueryBuilder(mount, filters, rules);
  });

  window.QueryBuilder = QueryBuilder;
})();
