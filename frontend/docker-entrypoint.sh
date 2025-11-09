#!/bin/sh
set -euo pipefail

LOCKFILE_HASH_FILE=".npm-lock.hash"
CURRENT_HASH="$(sha256sum package-lock.json | awk '{ print $1 }')"
STORED_HASH=""

if [ -f "$LOCKFILE_HASH_FILE" ]; then
  STORED_HASH="$(cat "$LOCKFILE_HASH_FILE")"
fi

if [ ! -d node_modules ] || [ "$CURRENT_HASH" != "$STORED_HASH" ]; then
  echo "Installing frontend dependencies..."
  npm ci
  echo "$CURRENT_HASH" > "$LOCKFILE_HASH_FILE"
else
  echo "Dependencies unchanged, skipping install."
fi

exec "$@"
