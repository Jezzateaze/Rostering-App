#!/usr/bin/env bash
set -euo pipefail

echo "🔧 Post-create: setting up workspace..."

# Node / frontend deps
if [ -d "frontend" ]; then
  echo "📦 Installing frontend deps..."
  pushd frontend >/dev/null
  corepack enable || true
  if [ -f yarn.lock ]; then
    yarn install --frozen-lockfile || yarn install
  else
    npm ci || npm install
  fi
  popd >/dev/null
fi

# Python / backend deps
if [ -d "backend" ]; then
  echo "🐍 Installing backend deps..."
  pushd backend >/dev/null
  python3 -m pip install --upgrade pip wheel setuptools
  if [ -f requirements.txt ]; then
    pip install -r requirements.txt
  elif [ -f pyproject.toml ]; then
    pip install .
  fi
  popd >/dev/null
fi

echo "✅ Post-create complete."
