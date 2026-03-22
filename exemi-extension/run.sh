#!/usr/bin/env bash
set -eu

ROOT="$(cd "$(dirname "$0")" && pwd)"
FRONTEND="$(cd "$ROOT/../exemi-frontend" && pwd)"

# 0) Initial exemi-frontend build into extension dist/ (Vite via Yarn in nix-shell)
nix-shell "$FRONTEND/shell.nix" --run "cd \"$FRONTEND\" && yarn build:extension"

# 1) Ensure dist/ has manifest + icons + content bundle
nix-shell "$ROOT/shell.nix" --run "cd \"$ROOT\" && yarn build"

# 2) Watch exemi-frontend → exemi-extension/dist/exemi-frontend
nix-shell "$FRONTEND/shell.nix" --run "cd \"$FRONTEND\" && yarn build:extension-watch" >"$ROOT/.vite-frontend-watch.log" 2>&1 &
FRONTEND_PID=$!

# 3) Watch extension content script
nix-shell "$ROOT/shell.nix" --run "cd \"$ROOT\" && yarn dev" >"$ROOT/.vite-watch.log" 2>&1 &
VITE_PID=$!

trap 'kill "$FRONTEND_PID" "$VITE_PID" 2>/dev/null || true' EXIT

# 4) Run Firefox with auto-reload in foreground
cd "$ROOT"
web-ext run -s dist
