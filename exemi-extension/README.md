# Exemi Browser Extension

Integrates Exemi into Canvas by injecting a **sidebar** on `*.instructure.com`. The sidebar is a small React shell (bundled as `dist/content.js`) that embeds the full **exemi-frontend** app in an **iframe** served from the extension package (`dist/exemi-frontend/`).

## Architecture

- **Content script** (`src/content.tsx`): Injected on Canvas only. Mounts UI inside a **shadow root** so Canvas CSS does not leak in or out.
- **Sidebar iframe**: `src` is `runtime.getURL("exemi-frontend/index.html")`. The iframe document lives on the extension origin (`moz-extension://…` / `chrome-extension://…`), not on Canvas, so it can call your API with **host permissions** (see `manifest.json`).
- **Canvas URL → app**: The content script tracks the Canvas page (pathname, query, full href) and sends updates to the iframe with `postMessage`. The frontend listens and exposes that data via React context (`exemi-frontend`); the iframe `src` stays fixed so **in-app state survives Canvas SPA navigations**.
- **exemi-frontend build**: No duplicated source. Vite builds the sibling [exemi-frontend](../exemi-frontend) with `EXEMI_EXTENSION_BUILD=1` so output goes to `exemi-extension/dist/exemi-frontend/` with `base: './'`. The extension uses **hash routing** in the iframe when the protocol is `moz-extension:` / `chrome-extension:` so React Router matches routes correctly (the real pathname is `/exemi-frontend/index.html`).
- **Backend / CORS**: `manifest.json` includes `host_permissions` for `https://exemi.au/`* and `https://www.exemi.au/*` (in addition to Canvas).

## Features

- Shadow DOM host so injected UI stays isolated from Canvas
- React sidebar + iframe-hosted **exemi-frontend** (full chat and auth flows)
- Injects only when Canvas looks logged in (`localStorage.canvas_session` and DOM fallbacks)
- `web_accessible_resources`: `exemi-frontend/` for Canvas origins

## Installation

```bash
# Frontend dependencies
cd exemi-frontend
nix-build shell.nix
nix-shell
yarn install
exit
cd ../

# Extension dependencies
cd exemi-extension
nix-build shell.nix
nix-shell
yarn install
exit
```

## Running (development)

From `exemi-extension`, use `run.sh`. It:

1. Builds **exemi-frontend** once into `dist/exemi-frontend/` (`yarn build:extension` inside `nix-shell` for the frontend tree).
2. Runs `yarn build` here once (content script + static copy).
3. Starts `yarn build:extension-watch` in **exemi-frontend** (rebuilds the iframe bundle on change).
4. Starts `yarn dev` here (`vite build --watch` for `dist/content.js`).
5. Launches Firefox with `web-ext run -s dist` (reloads the extension on `dist/` changes).

```bash
cd exemi-extension
. run.sh
```

Logs from the two watchers go to `.vite-frontend-watch.log` and `.vite-watch.log` in this directory.

## Production-style build

```bash
cd exemi-frontend && nix-shell --run "yarn build:extension"
cd ../exemi-extension && nix-shell --run "yarn build"
```

Load `exemi-extension/dist` as an unpacked extension in the browser.

## Files of note


| Path                      | Role                                                                                                        |
| ------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `manifest.json`           | Matches Canvas, `content_scripts`, `web_accessible_resources`, `host_permissions`                           |
| `src/content.tsx`         | Inject, sidebar, iframe `src`, `postMessage` bridge                                                         |
| `vite.config.ts`          | Library IIFE → `dist/content.js`, `emptyOutDir: false` so `exemi-frontend/` in `dist/` is kept during watch |
| `scripts/copy-static.mjs` | Copies `manifest.json` and icons into `dist/`                                                               |


