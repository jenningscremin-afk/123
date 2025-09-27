#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Running smoke tests in: $ROOT_DIR"

failures=0
checked=0

# Find .html files under repository (skip node_modules if any)
while IFS= read -r -d '' file; do
  checked=$((checked+1))
  echo "\nChecking: $file"
  if [ ! -s "$file" ]; then
    echo "  ERROR: file is empty"
    failures=$((failures+1))
    continue
  fi

  if ! grep -qi "<html" "$file"; then
    echo "  WARNING: no <html> tag found"
    # treat missing <html> as a failure for this smoke test
    failures=$((failures+1))
    continue
  fi

  echo "  OK"
done < <(find . -type f -name '*.html' -print0)

echo "\nChecked files: $checked"
if [ "$failures" -ne 0 ]; then
  echo "Failures: $failures"
  exit 2
else
  echo "All smoke checks passed"
  exit 0
fi
