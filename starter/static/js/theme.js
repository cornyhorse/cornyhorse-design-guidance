/* Theme control. The only JavaScript this kit ships.
 *
 * Light / Auto / Dark. "light" and "dark" pin the theme through data-bs-theme on <html>;
 * "auto" removes the attribute so the page follows the OS (prefers-color-scheme). The choice
 * is kept in localStorage under "ch-theme".
 *
 * Loaded from <head>, synchronously, as an external file (the Content-Security-Policy allows
 * no inline script), so a saved choice is applied before first paint and the page never flashes.
 * No libraries, no Bootstrap JS.
 */
(function () {
  var KEY = 'ch-theme';
  var root = document.documentElement;

  function read() {
    // Anything that is not one of the two pinned values means "follow the OS", so a value left
    // behind by an older build cannot leave the three buttons with none of them pressed.
    try {
      var stored = localStorage.getItem(KEY);
      return stored === 'light' || stored === 'dark' ? stored : 'auto';
    } catch (e) { return 'auto'; }
  }
  function apply(mode) {
    if (mode === 'light' || mode === 'dark') root.setAttribute('data-bs-theme', mode);
    else root.removeAttribute('data-bs-theme');
  }
  function sync(mode) {
    var buttons = document.querySelectorAll('[data-theme-set]');
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].setAttribute('aria-pressed', String(buttons[i].getAttribute('data-theme-set') === mode));
    }
  }
  function choose(mode) {
    apply(mode);
    sync(mode);
  }

  apply(read());
  document.addEventListener('DOMContentLoaded', function () { sync(read()); });
  document.addEventListener('click', function (e) {
    var b = e.target.closest ? e.target.closest('[data-theme-set]') : null;
    if (!b) return;
    var mode = b.getAttribute('data-theme-set');
    // Keep the mode we just applied rather than re-reading storage: if setItem throws (Safari
    // private mode, storage disabled) the page is pinned while aria-pressed would snap back.
    try { localStorage.setItem(KEY, mode); } catch (err) { /* still apply for this view */ }
    choose(mode);
  });
})();
