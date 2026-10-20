# Front end: self-hosted, enforced, almost no JavaScript

The rule: **a page loads nothing from outside this server.** No CDN, no Google Fonts, no analytics, no remote images.
Everything the site shows is in the repository and served by the site, and the browser is told to refuse anything else.

Why: a site that works when the internet is slow, when a CDN is down, or when it sits on a private network; no third
party sees who loads which page; nothing changes underneath you because a CDN pushed a new version; and every file is
auditable in git.

## Static files in the repository

Everything under `static/` ships with the project:

```
static/
  css/       tokens.css  components.css  app.css  fonts.css     (ours)
  js/        theme.js                                           (ours, ~50 lines)
  img/       favicon.svg
  vendor/    bootstrap/  bootstrap-icons/  fonts/  README.md    (third party, with hashes)
```

**WhiteNoise serves them** from the web container, so there is no nginx static mount and no CDN. In production:

- `collectstatic` runs at **image build** time (it needs no database and no real secret), producing hashed, gzipped copies
  in `/app/staticfiles`.
- `WhiteNoiseMiddleware` sits **right after** `SecurityMiddleware`.
- `STORAGES["staticfiles"]` is `config.storage.ManifestStaticFilesStorage`: WhiteNoise's compressed manifest storage with the
  one fix described below. Hashed names get `Cache-Control: max-age=315360000, public, immutable`; the manifest rewrites the
  `url()` references inside `fonts.css`, so the font files are hashed too.
- Where something else in your stack already serves `/static/` (say, a reverse proxy mounting the collected directory),
  you may skip WhiteNoise, but then that has to be written down in the project's `DEVELOPING.md`.

### The source-map trap

`bootstrap.min.css` ends with `/*# sourceMappingURL=bootstrap.min.css.map */` and we do not ship the `.map` file (it only
helps an open DevTools). Django's hashing storage treats a reference to a missing file as fatal, so `collectstatic` stops with
`The file 'vendor/bootstrap/bootstrap.min.css.map' could not be found`. Verified against Django 6.1 and WhiteNoise 6.12: the
plain `CompressedManifestStaticFilesStorage` fails; the subclass in `config/storage.py` drops that one pattern and leaves the
vendored file **byte-identical**, so its recorded checksum stays checkable. `tests/test_production_static.py` runs the real
`collectstatic` with the production storage. A dev-only test would never have shown this.

## The vendoring rule

Third-party front-end files are allowed, under strict conditions:

1. **The owner approves the exact list first.** Name each file, source URL, version and size. Do not download "while you are
   at it". The starter already carries the approved baseline, so a new project needs no downloads at all.
2. **Fetch with `curl` from a pinned version**, once, and commit the bytes untouched. The reference files came from the npm
   packages through the jsdelivr mirror (`https://cdn.jsdelivr.net/npm/<package>@<version>/<path>`); no Node was involved.
3. **Record it** in `static/vendor/README.md`: package, version, what it is used for, licence, source URL, SHA-256.
4. **Ship the licence text** next to the files.
5. **A test checks it.** `tests/test_vendor_assets.py` fails when a file's hash differs from the README, when a vendored file is
   unrecorded, when an unapproved package appears, when a licence is missing, or when any `.js` or icon-font file is vendored.
   Widening the approved list means editing that test in the same change, on purpose.

What the starter vendors (all redistributable; licences are in the folders):

| Package | Version | Used for |
| --- | --- | --- |
| Bootstrap | 5.3.8 | `bootstrap.min.css` **only**: grid, reboot, utilities. No JavaScript bundle, no Popper. |
| Bootstrap Icons | 1.13.1 | individual SVGs, built into one inline sprite. The icon font is not shipped. |
| IBM Plex Sans, Plex Mono | 5.3.0 (`@fontsource`) | latin subset, weights 400/500/600, `woff2`, `font-display: swap` |

### Icons: an inline SVG sprite, never an icon font

An icon font that fails to load turns every icon-only button into an empty box (the reference project verified this by
removing the font). So `scripts/build_icon_sprite.py` assembles the few vendored SVGs into one `sprite.svg`, templates draw
an icon with `{% icon "name" %}`, and two tests keep it honest: the sprite must equal what the script builds, and an icon may
not be vendored without being used (or used without being vendored). `make sprite` rebuilds it.

## Content-Security-Policy: enforced, not promised

```python
SECURE_CSP = {
    "default-src": ["'self'"], "script-src": ["'self'"], "style-src": ["'self'"],
    "img-src": ["'self'", "data:"], "font-src": ["'self'"], "connect-src": ["'self'"],
    "object-src": ["'none'"], "base-uri": ["'self'"], "form-action": ["'self'"], "frame-ancestors": ["'none'"],
}
```

Django 6.0 added `django.middleware.csp.ContentSecurityPolicyMiddleware` and the `SECURE_CSP` setting, so no code of our own is
needed (the reference project, written on Django 5, carried a 29-line middleware; if you are stuck on 5.2 LTS, that is the
fallback: send the same header from a middleware placed before `CommonMiddleware`). The middleware sits **early** so error pages
carry the policy too.

`data:` is allowed for **images only**, because Bootstrap's CSS embeds a few `data:` SVGs (checkbox ticks); `tests/test_csp.py`
fails if `data:` appears anywhere else, if `'unsafe-inline'` or `'unsafe-eval'` appears at all, or if the policy differs from
the one above by a single source.

What the policy forbids, and what to do instead:

| Forbidden | Do this |
| --- | --- |
| Inline `<script>` and `onclick=` handlers | External file in `static/js/`, event listeners attached in it |
| `<style>` blocks and `style=""` attributes | Classes in `components.css` / `app.css` |
| A bar whose width comes from data | Inline SVG: `<rect width="46.4">`. The width is an SVG *attribute*, not a style (`{% usage_bar %}`) |
| A CDN link, Google Fonts, remote image | Vendor it ([above](#the-vendoring-rule)) or leave it out |
| `<meta http-equiv="refresh">` | Nothing in the starter needs it; it also reloads the page and closes folds the user opened |
| Swagger UI / DRF browsable API from a CDN | Not needed by default (no DRF). If you add an API UI, self-host it, and pin the exemption list in a test |

### The self-hosting test

`tests/test_self_hosted.py` renders **every page** (signed out and in, empty and populated, an error state, every message
level) and fails on anything a browser would fetch or run from elsewhere: absolute or protocol-relative URLs in any URL
attribute, `<script>` without a same-origin `src`, inline handlers, `<style>`, `style=""`, `<iframe>`, `preconnect`/`preload`
links and `http-equiv`. It scans every served stylesheet for `@import` and external `url()`, and checks that every static file
a page points to exists. The scanner is itself tested against a list of bad snippets so it cannot go quiet.

**When you add a page, add it to `pages()` in that file.** A page that is not listed is not protected.

## JavaScript: very little, all custom

Strictest option first; stop at the first one that works.

1. **None.** `<details>` for folds and menus, a GET form for search and filters (a server-rendered results page), POST forms with
   a CSRF token for actions. Needs no script and works with scripts disabled.
2. **A small hand-written vanilla file**: external (the CSP allows no inline script), no build step, no module bundler, no
   dependencies. The starter ships exactly one, `theme.js` (~50 lines), for the Light/Auto/Dark control. A test caps the
   JavaScript to that one file, forbids `fetch(`, `XMLHttpRequest`, `WebSocket`, `eval(` and URLs in it, and caps its length. Ask
   before adding a second.
3. **A vendored library, only if it is incredibly popular** (a household name, long-maintained, MIT-style licensed), and
   only with the owner's OK, recorded like any other vendored file. Never a framework, never a bundler, never from npm.

Progressive enhancement over single-page apps: a live search dropdown, say, is optional sugar on top of a working GET form
and costs about 30 lines of `fetch` and a JSON endpoint, so it is a decision to ask about, not a default.

## Theme: light, dark and auto, with no flash

- Colours are tokens in `tokens.css`, each written **once** as `light-dark(<light>, <dark>)`, with `color-scheme: light dark` on
  `:root`. The page follows the OS by default.
- The Light / Auto / Dark control sets `data-bs-theme` on `<html>` (Bootstrap's own hook), and "Auto" removes it. The choice
  lives in `localStorage` under `ch-theme`.
- `theme.js` is loaded **synchronously from `<head>`, before the stylesheets**, so a saved choice is applied before first paint
  and the page never flashes the wrong theme. A test asserts the order.
- Browser floor: `light-dark()` needs Chrome/Edge 123, Safari 17.5, Firefox 120 (also used: `color-mix()`, container queries).
  There is no fallback; on an older browser the colour tokens are invalid and the page loses its colours. That is fine for a
  private tool used from current browsers; **say so in the project README**. If older devices matter, add an
  `@supports not (color: light-dark(#000, #fff))` block that sets the light values only.
- Bootstrap still reads a few colours as `r, g, b` triplets, which `light-dark()` cannot produce, so those few are written out
  per mode at the bottom of `tokens.css`. Everything the kit styles itself uses the `--ch-*` tokens and avoids Bootstrap's
  `.bg-*`, `.text-*` and `.link-*` colour utilities.

## Checks to run before calling a page done

The tests catch the structural rules. These need a real browser:

- Open it at **320, 375, 768, 1000, 1280 and 1440 px**, light and dark. No horizontal scroll at 320.
- Contrast and focus checked with a **script run in the page** against computed styles (open folds first so hidden rows are
  included), not by eye. Targets: body and secondary text >= 7:1, muted text >= 4.5:1, status text on its tint >= 5.6:1, marks
  and control borders >= 3:1.
- Every control shows a visible focus indicator; the skip link works; touch targets are 44 px on phones.
- DevTools **Network** shows requests to one origin only. (The starter was checked this way: 13 resources, one origin, six
  font files loaded, zero `style` attributes, no console errors.)
