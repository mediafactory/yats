# Frontend assets (Tailwind CSS + Alpine.js)

YATS uses **Tailwind CSS** (compiled via the standalone CLI — no Node required)
and **Alpine.js** for interactivity. There is intentionally no `package.json` /
npm pipeline; the deploy host stays Node-free.

## Files

- `tailwind.input.css` — Tailwind entrypoint + YATS `@layer components` classes.
- `../tailwind.config.js` — config (content globs, brand theme).
- Output: `../modules/yats/static/tailwind.css` (served by Django's
  `AppDirectoriesFinder`, then `collectstatic`). **Committed** to the repo so a
  deploy never strictly needs the binary, but CI/deploy rebuilds it (see
  `deploy/bootstrap.sh`).

## Pinned version

Tailwind **v3.4.x** standalone CLI. Pin matches `deploy/bootstrap.sh`.

## Build locally (macOS)

```sh
# one-time: download the standalone binary into ./.bin (gitignored)
mkdir -p .bin
curl -sL -o .bin/tailwindcss \
  https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.17/tailwindcss-macos-arm64
chmod +x .bin/tailwindcss

# build once (minified, for committing)
./.bin/tailwindcss -i assets/tailwind.input.css -o modules/yats/static/tailwind.css --minify

# OR watch during development
./.bin/tailwindcss -i assets/tailwind.input.css -o modules/yats/static/tailwind.css --watch
```

On Linux x64 use the `tailwindcss-linux-x64` asset instead — that is what
`deploy/bootstrap.sh` downloads automatically.

## Alpine.js

`modules/yats/static/alpine.min.js` is vendored (loaded with `defer` in
`base.html`). Update it by replacing that file with a new pinned release.
