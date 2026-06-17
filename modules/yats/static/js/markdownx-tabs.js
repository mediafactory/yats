/*
 * Wrap the django-markdownx editor/preview in Tailwind tabs.
 * Replaces the old Bootstrap tabs + jQuery used on docs edit/new pages.
 * The markdownx widget provides #id_text (textarea) and .markdownx-preview.
 * Labels are passed via data attributes so the strings stay translatable.
 */
document.addEventListener('DOMContentLoaded', function () {
  var mdx = document.querySelector('.markdownx');
  if (!mdx) return;

  var script = document.currentScript || document.querySelector('script[src*="markdownx-tabs"]');
  var editLabel = (script && script.dataset.editLabel) || 'edit';
  var previewLabel = (script && script.dataset.previewLabel) || 'preview';

  var tabBtn = function (tab, label, active) {
    return '<li><button type="button" data-tab="' + tab + '" class="md-tab inline-block px-4 py-2 border-b-2 ' +
      (active ? 'border-brand text-brand font-medium' : 'border-transparent text-gray-500 hover:text-gray-700') +
      '">' + label + '</button></li>';
  };

  var tabs = document.createElement('div');
  tabs.innerHTML =
    '<ul class="flex border-b border-gray-200 mb-3" role="tablist">' +
      tabBtn('edit', editLabel, true) + tabBtn('preview', previewLabel, false) +
    '</ul>' +
    '<div data-pane="edit"></div>' +
    '<div data-pane="preview" style="display:none"></div>';
  mdx.prepend(tabs);

  var idText = document.getElementById('id_text');
  if (idText) tabs.querySelector('[data-pane="edit"]').appendChild(idText);
  var preview = mdx.querySelector('.markdownx-preview');
  if (preview) tabs.querySelector('[data-pane="preview"]').appendChild(preview);

  tabs.querySelectorAll('.md-tab').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var target = btn.getAttribute('data-tab');
      tabs.querySelectorAll('.md-tab').forEach(function (b) {
        var on = b === btn;
        b.classList.toggle('border-brand', on);
        b.classList.toggle('text-brand', on);
        b.classList.toggle('font-medium', on);
        b.classList.toggle('border-transparent', !on);
        b.classList.toggle('text-gray-500', !on);
      });
      tabs.querySelectorAll('[data-pane]').forEach(function (p) {
        p.style.display = p.getAttribute('data-pane') === target ? '' : 'none';
      });
    });
  });
});
