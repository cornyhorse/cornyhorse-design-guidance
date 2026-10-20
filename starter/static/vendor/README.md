# Vendored front-end assets

Everything a page loads comes from this server. This directory holds the only third-party files in the
front end; nothing is fetched from a CDN, Google Fonts or anywhere else when a page loads, and a
Content-Security-Policy makes the browser refuse anything that is not same-origin.
`tests/test_vendor_assets.py` checks every hash below against the file on disk.

These files were copied byte for byte from a project that fetched them once, at build time, from the npm
packages through the jsdelivr mirror (`https://cdn.jsdelivr.net/npm/<package>@<version>/<path>`). No Node, npm
or build step is involved, then or now.

| Package | Version | Used for | Licence |
| --- | --- | --- | --- |
| `bootstrap` | 5.3.8 | `dist/css/bootstrap.min.css` only. No JavaScript bundle, no Popper | MIT |
| `bootstrap-icons` | 1.13.1 | individual `icons/*.svg` files (only the ones the pages use), assembled into one SVG sprite. The icon font is not shipped | MIT |
| `@fontsource/ibm-plex-sans` | 5.3.0 | IBM Plex Sans, latin subset, 400/500/600, `woff2` | SIL OFL 1.1 |
| `@fontsource/ibm-plex-mono` | 5.3.0 | IBM Plex Mono, latin subset, 400/500/600, `woff2` | SIL OFL 1.1 |

## Licences

The licence text of each package sits next to its files:

- Bootstrap and Bootstrap Icons: MIT, Copyright The Bootstrap Authors.
- IBM Plex: SIL Open Font License 1.1, Copyright IBM Corp. The OFL allows bundling and use in a web page;
  the fonts are not sold by themselves and are not renamed or modified here.

## Notes

- `bootstrap.min.css` ends with a `sourceMappingURL` comment for a `.map` file that is not shipped. Browsers read
  it only while DevTools is open. The file is left byte-identical so the hash below stays checkable, and
  `config/storage.py` stops Django's hashing storage from treating the missing map as an error.
- Bootstrap's CSS contains `url("data:image/svg+xml,...")` images (form check marks and so on). That is why the
  policy allows `img-src data:`. It requests nothing.
- `sprite.svg` is derived, not downloaded: `python3 scripts/build_icon_sprite.py` assembles it from `icons/*.svg`,
  and a test fails if it is stale or if an icon is vendored but unused. Pages draw an icon with
  `<svg class="bi"><use href="/static/vendor/bootstrap-icons/sprite.svg#name"/></svg>` (`{% icon "name" %}` in
  templates).

## Files

| File | Package | Version | Source | SHA-256 |
| --- | --- | --- | --- | --- |
| `static/vendor/bootstrap/LICENSE` | bootstrap | 5.3.8 | <https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/LICENSE> | `4620c84ad5ce8602ff65640ed6b7c8b78ebb9e036584f0ebc1ccc88206a4bb51` |
| `static/vendor/bootstrap/bootstrap.min.css` | bootstrap | 5.3.8 | <https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css> | `d85327d99c7a3ee1f9b5d0500d1370acea3ad2db39c163c2f51f232baedbdede` |
| `static/vendor/bootstrap-icons/LICENSE` | bootstrap-icons | 1.13.1 | <https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/LICENSE> | `0fb3e11bd57e896c5a512afd64864d28a37de45d19835016c87ca1ad19ead969` |
| `static/vendor/bootstrap-icons/icons/arrow-repeat.svg` | bootstrap-icons | 1.13.1 | <https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/icons/arrow-repeat.svg> | `2705f6572d27f2330329a5f87e6d861065d221ee56d60870f60486d2ab747c85` |
| `static/vendor/bootstrap-icons/icons/box-arrow-in-right.svg` | bootstrap-icons | 1.13.1 | <https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/icons/box-arrow-in-right.svg> | `3d2bf903e7f8035c3c503af7d5f9500311f29e5cec1654809ba5f597898ab03c` |
| `static/vendor/bootstrap-icons/icons/box-arrow-right.svg` | bootstrap-icons | 1.13.1 | <https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/icons/box-arrow-right.svg> | `a1ec3378190a414029563bd1326d8de6d3c587326cd506b78d30c5c059cb9107` |
| `static/vendor/bootstrap-icons/icons/check-circle-fill.svg` | bootstrap-icons | 1.13.1 | <https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/icons/check-circle-fill.svg> | `f6f5d971091787219c4226c5bf68a6ebd4d976c91bd90fc52ba3b422589b2dc8` |
| `static/vendor/bootstrap-icons/icons/chevron-right.svg` | bootstrap-icons | 1.13.1 | <https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/icons/chevron-right.svg> | `51b9c4168b12b378acde3131234ffe2b2fa5ed3c80a944a7dc864bb515b469cf` |
| `static/vendor/bootstrap-icons/icons/circle-half.svg` | bootstrap-icons | 1.13.1 | <https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/icons/circle-half.svg> | `65de347262cd8a8a1e852e7af6008b10e45f417b61db00dd54e51e5fd13ccdd5` |
| `static/vendor/bootstrap-icons/icons/exclamation-triangle-fill.svg` | bootstrap-icons | 1.13.1 | <https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/icons/exclamation-triangle-fill.svg> | `3677ae9c1f8e2fc3d95f71384bf417d9dc3af79007e363f3e0ccef2218fff290` |
| `static/vendor/bootstrap-icons/icons/grid-1x2.svg` | bootstrap-icons | 1.13.1 | <https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/icons/grid-1x2.svg> | `5ab371c57d3fc9d7fdb0662f49e39bd060dc66f8e5c4da4de6043b74226dd472` |
| `static/vendor/bootstrap-icons/icons/hourglass-split.svg` | bootstrap-icons | 1.13.1 | <https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/icons/hourglass-split.svg> | `7c2c5e404704cc4689cef2f69bb353bc48d55ca2901a34616e908e1a378c5fcf` |
| `static/vendor/bootstrap-icons/icons/moon.svg` | bootstrap-icons | 1.13.1 | <https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/icons/moon.svg> | `c68e340f8beec2d9d078fd36c580778fc0c01f984c207f0a804919876c406d0a` |
| `static/vendor/bootstrap-icons/icons/pause-circle.svg` | bootstrap-icons | 1.13.1 | <https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/icons/pause-circle.svg> | `c240a16fb9eeb6bf41f2473395d51cd75bc892332295dd03edcc68f7d130f158` |
| `static/vendor/bootstrap-icons/icons/person.svg` | bootstrap-icons | 1.13.1 | <https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/icons/person.svg> | `e071db1bfc90bd30bc621d14e9b1c9b5d195b932d7027d65e1e30fbd9ffbf6c9` |
| `static/vendor/bootstrap-icons/icons/pie-chart-fill.svg` | bootstrap-icons | 1.13.1 | <https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/icons/pie-chart-fill.svg> | `ea29132f3f822794d8d6ede40aefd097f3253351067edffcbe87e8cffd1ef664` |
| `static/vendor/bootstrap-icons/icons/question-circle.svg` | bootstrap-icons | 1.13.1 | <https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/icons/question-circle.svg> | `6ec0095139e8e6f35e47d4de1968846d57f3006a0d3074651637e0bcc80c8c9c` |
| `static/vendor/bootstrap-icons/icons/sun.svg` | bootstrap-icons | 1.13.1 | <https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/icons/sun.svg> | `72be1ffbedea58a5cf68b136627439b42c26643765f230fc807496998ed2141d` |
| `static/vendor/bootstrap-icons/icons/wifi-off.svg` | bootstrap-icons | 1.13.1 | <https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/icons/wifi-off.svg> | `1c3990b804510c490194e0666d232596bcdbb1d18bdbceb03173adfae24cf406` |
| `static/vendor/bootstrap-icons/icons/x-octagon-fill.svg` | bootstrap-icons | 1.13.1 | <https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/icons/x-octagon-fill.svg> | `6a99d6ebf8b351a5143d50e9094fe00341d3e8dba867f68368728eb100a3a762` |
| `static/vendor/bootstrap-icons/sprite.svg` | derived from the icons above | 1.13.1 | `scripts/build_icon_sprite.py` | `f766cde30b2411465d19109fe303b0437165e5b04448ae6f83b301af3c9d7808` |
| `static/vendor/fonts/ibm-plex-mono/LICENSE` | @fontsource/ibm-plex-mono | 5.3.0 | <https://cdn.jsdelivr.net/npm/@fontsource/ibm-plex-mono@5.3.0/LICENSE> | `23b0a9d0c6d3f140a0b77e483c5cfa6bba574325ef5cb189ed9f2fec4884533f` |
| `static/vendor/fonts/ibm-plex-mono/ibm-plex-mono-latin-400-normal.woff2` | @fontsource/ibm-plex-mono | 5.3.0 | <https://cdn.jsdelivr.net/npm/@fontsource/ibm-plex-mono@5.3.0/files/ibm-plex-mono-latin-400-normal.woff2> | `08949f728dc52d528e69b1667d15c89a5686a4ee9a296ff90983985f99c380f7` |
| `static/vendor/fonts/ibm-plex-mono/ibm-plex-mono-latin-500-normal.woff2` | @fontsource/ibm-plex-mono | 5.3.0 | <https://cdn.jsdelivr.net/npm/@fontsource/ibm-plex-mono@5.3.0/files/ibm-plex-mono-latin-500-normal.woff2> | `01d285447409c8a588692162439a038b8cbd7871309ee20267b0d2d91c6e8e22` |
| `static/vendor/fonts/ibm-plex-mono/ibm-plex-mono-latin-600-normal.woff2` | @fontsource/ibm-plex-mono | 5.3.0 | <https://cdn.jsdelivr.net/npm/@fontsource/ibm-plex-mono@5.3.0/files/ibm-plex-mono-latin-600-normal.woff2> | `0d1f0b8d0722224e32e9f28261bdc86c79115be73444ae5eceb73976a1bcdf83` |
| `static/vendor/fonts/ibm-plex-sans/LICENSE` | @fontsource/ibm-plex-sans | 5.3.0 | <https://cdn.jsdelivr.net/npm/@fontsource/ibm-plex-sans@5.3.0/LICENSE> | `d0283623ef57e722fd0eb688a8041589670c608ab780cd3612d06ba6f153d3fd` |
| `static/vendor/fonts/ibm-plex-sans/ibm-plex-sans-latin-400-normal.woff2` | @fontsource/ibm-plex-sans | 5.3.0 | <https://cdn.jsdelivr.net/npm/@fontsource/ibm-plex-sans@5.3.0/files/ibm-plex-sans-latin-400-normal.woff2> | `3b646991d30055a93a4ecc499713d4347953a74a947ecab435ab72070cbdab0e` |
| `static/vendor/fonts/ibm-plex-sans/ibm-plex-sans-latin-500-normal.woff2` | @fontsource/ibm-plex-sans | 5.3.0 | <https://cdn.jsdelivr.net/npm/@fontsource/ibm-plex-sans@5.3.0/files/ibm-plex-sans-latin-500-normal.woff2> | `0717336fb31fcdcde4b8deb3675bb4a0f7f6d484864afcd6751ac29975962203` |
| `static/vendor/fonts/ibm-plex-sans/ibm-plex-sans-latin-600-normal.woff2` | @fontsource/ibm-plex-sans | 5.3.0 | <https://cdn.jsdelivr.net/npm/@fontsource/ibm-plex-sans@5.3.0/files/ibm-plex-sans-latin-600-normal.woff2> | `8960851d691c054ed38e259bdcf1a6190d157b4203ed5bb32c632a863fb8ec2f` |

## Adding or updating an asset

Anything not listed above needs the owner's go-ahead first (see docs/frontend.md, "The vendoring rule").

1. Fetch the file from the pinned package URL pattern above (an icon is
   `https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/icons/<name>.svg`) into the matching folder.
2. For an icon, run `python3 scripts/build_icon_sprite.py` to rebuild `sprite.svg`.
3. Add its row, with `sha256sum` of the file, to the table above. The test fails until you do.
