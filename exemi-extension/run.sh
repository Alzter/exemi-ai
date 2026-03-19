#!/usr/bin/env bash
set -eu

# 1) Ensure dist/ has manifest + icons + initial bundle
nix-shell --run "yarn build"

# 2) Keep rebuilding bundle in background (don't steal stdin)
nix-shell --run "yarn dev -- --force" >.vite-watch.log 2>&1 &
VITE_PID=$!
trap 'kill "$VITE_PID" 2>/dev/null || true' EXIT

# 3) Run Firefox with auto-reload in foreground
web-ext run -s dist