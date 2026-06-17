/*
 * Hover image preview, replacing the old jQuery-UI .tooltip({items:"[dataimg]"}).
 * Any element with a `dataimg` attribute shows that image in a floating preview
 * that tracks the cursor.
 */
(function () {
  var tip = null;

  function ensureTip() {
    if (tip) return tip;
    tip = document.createElement('div');
    tip.style.cssText =
      'position:fixed;z-index:70;pointer-events:none;display:none;' +
      'background:#fff;border:1px solid #ccc;border-radius:6px;padding:4px;' +
      'box-shadow:0 5px 15px rgba(0,0,0,.2);';
    tip.innerHTML = '<img style="display:block;max-width:300px;height:auto" />';
    document.body.appendChild(tip);
    return tip;
  }

  function move(e) {
    if (!tip || tip.style.display === 'none') return;
    var x = e.clientX + 16, y = e.clientY + 16;
    // keep it on-screen
    var w = tip.offsetWidth, h = tip.offsetHeight;
    if (x + w > window.innerWidth) x = e.clientX - w - 16;
    if (y + h > window.innerHeight) y = e.clientY - h - 16;
    tip.style.left = x + 'px';
    tip.style.top = y + 'px';
  }

  document.addEventListener('mouseover', function (e) {
    var el = e.target.closest('[dataimg]');
    if (!el) return;
    var t = ensureTip();
    t.querySelector('img').src = el.getAttribute('dataimg');
    t.style.display = 'block';
    move(e);
  });
  document.addEventListener('mousemove', move);
  document.addEventListener('mouseout', function (e) {
    if (e.target.closest('[dataimg]') && tip) tip.style.display = 'none';
  });
})();
