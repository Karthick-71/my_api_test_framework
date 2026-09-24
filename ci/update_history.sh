#!/usr/bin/env bash
# Append this CI run to the cross-build history and render the history report.
#
# The store (one small JSON file per build) lives on the `test-history` branch,
# outside any single workflow run, so it survives artifact expiry and
# workspace cleanup. That is the point of the tool: history that outlives
# the builds that produced it.
set -euo pipefail

: "${BUILD_NUMBER:?}" "${BUILD_URL:?}" "${BRANCH_NAME:?}"
JUNIT="reports/junit-triage.xml"
HISTORY_DIR=".history"
STORE="$HISTORY_DIR/store"
OUT="site/history/index.html"

git config --global user.name "github-actions[bot]"
git config --global user.email "41898282+github-actions[bot]@users.noreply.github.com"

# Check out the history branch into its own worktree, creating it on the first run.
if git ls-remote --exit-code --heads origin test-history >/dev/null 2>&1; then
  git fetch --depth 1 origin test-history
  git worktree add "$HISTORY_DIR" FETCH_HEAD
  git -C "$HISTORY_DIR" checkout -B test-history
else
  git worktree add --detach "$HISTORY_DIR"
  git -C "$HISTORY_DIR" checkout --orphan test-history
  git -C "$HISTORY_DIR" rm -rfq .
  printf '# Test history store\n\nOne JSON file per CI build, written by ci/update_history.sh on main.\n' > "$HISTORY_DIR/README.md"
fi

INIT=()
[ -d "$STORE" ] || INIT=(--init) # first run only; afterwards a missing store should fail loudly

if [ ! -f "$JUNIT" ]; then
  echo "No $JUNIT from the test job: re-rendering existing history without recording this build."
  node .triage-tool/src/triage-report.js ${INIT[@]+"${INIT[@]}"} --store "$STORE" --out "$OUT" \
    --job "my_api_test_framework"
else
  node .triage-tool/src/triage-report.js ${INIT[@]+"${INIT[@]}"} --junit "$JUNIT" --build "$BUILD_NUMBER" \
    --branch "$BRANCH_NAME" --env dev --url "$BUILD_URL" --job "my_api_test_framework" \
    --store "$STORE" --out "$OUT"
fi

git -C "$HISTORY_DIR" add -A
if git -C "$HISTORY_DIR" diff --cached --quiet; then
  echo "History store unchanged."
else
  git -C "$HISTORY_DIR" commit -qm "Record build #$BUILD_NUMBER"
  git -C "$HISTORY_DIR" push -q origin test-history
  echo "Recorded build #$BUILD_NUMBER on test-history."
fi
