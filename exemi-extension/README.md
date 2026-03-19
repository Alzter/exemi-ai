# Exemi Browser Extension
Integrates the Exemi chat UI into the Canvas website by injecting a floating **Exemi Chat** sidebar into any Canvas page on `*.instructure.com`.

## Features
- Shadow DOM injected UI so it won’t break Canvas styling
- React-based sidebar (bundled into `dist/content.js`)
- Only injects when Canvas appears to be logged in (based on `localStorage.canvas_session` and Canvas DOM fallbacks)
- Dev workflow reloads the extension automatically in Firefox

## Installation
```bash
cd exemi-extension
nix-build shell.nix
nix-shell
yarn install
exit
```

## Running

### Development
To use the Exemi Extension in a development environment,
you can use Firefox's ``web-ext`` tool (provided), which will
create a Firefox browser client with the extension and
reload the extension every time the source files are
changed.

```bash
cd exemi-extension
. run.sh
```