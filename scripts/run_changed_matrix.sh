#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

INPUT_PATH="$ROOT_DIR/data/test_cases.xlsx"
ENVIRONMENT="${TEST_ENV:-preprod}"
PLATFORM="all"
APPIUM_URL="${APPIUM_SERVER_URL:-http://127.0.0.1:4723}"
ANDROID_APP="$ROOT_DIR/app/app-release.apk"
IOS_APP="$ROOT_DIR/app/Runner.app"
IOS_REAL_APP=""
REPORT_ROOT="$ROOT_DIR/report/changed-device-matrix"
PYTHON_BIN="${PYTHON_BIN:-}"
DEVICE_ARGS=()

usage() {
  cat <<'EOF'
Usage: scripts/run_changed_matrix.sh [options]

Validate Excel, apply managed Feature changes, then run every added/modified
active scenario concurrently on every selected Android and iOS device.

Options:
  --input PATH          Registry workbook (default: data/test_cases.xlsx)
  --env NAME            Test environment (default: preprod)
  --platform VALUE      all, android, or ios (default: all)
  --device UDID         Restrict to a device; repeat for multiple devices
  --appium-url URL      Appium server URL (default: http://127.0.0.1:4723)
  --android-app PATH    Android APK path
  --ios-app PATH        iOS simulator .app path
  --ios-real-app PATH   Signed .ipa or .app for physical iOS devices
  --report-root PATH    Report parent directory
  --python PATH         Python interpreter (default: .venv/bin/python)
  -h, --help            Show this help

Exit codes:
  0  No pending runnable changes, or every changed case passed on every device
  1  At least one changed case failed on at least one device
  2  Validation, collection, device, Appium, app, lock, or I/O error
EOF
}

require_value() {
  if [[ $# -lt 2 || -z "$2" ]]; then
    echo "[changed-matrix] ERROR: $1 requires a value." >&2
    exit 2
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input)
      require_value "$@"
      INPUT_PATH="$2"
      shift 2
      ;;
    --env)
      require_value "$@"
      ENVIRONMENT="$2"
      shift 2
      ;;
    --platform)
      require_value "$@"
      PLATFORM="$2"
      shift 2
      ;;
    --device)
      require_value "$@"
      DEVICE_ARGS+=(--device "$2")
      shift 2
      ;;
    --appium-url)
      require_value "$@"
      APPIUM_URL="$2"
      shift 2
      ;;
    --android-app)
      require_value "$@"
      ANDROID_APP="$2"
      shift 2
      ;;
    --ios-app)
      require_value "$@"
      IOS_APP="$2"
      shift 2
      ;;
    --ios-real-app)
      require_value "$@"
      IOS_REAL_APP="$2"
      shift 2
      ;;
    --report-root)
      require_value "$@"
      REPORT_ROOT="$2"
      shift 2
      ;;
    --python)
      require_value "$@"
      PYTHON_BIN="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[changed-matrix] ERROR: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$PLATFORM" != "all" && "$PLATFORM" != "android" && "$PLATFORM" != "ios" ]]; then
  echo "[changed-matrix] ERROR: --platform must be all, android, or ios." >&2
  exit 2
fi

if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
    PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  else
    echo "[changed-matrix] ERROR: Python was not found." >&2
    exit 2
  fi
elif [[ "$PYTHON_BIN" != */* ]]; then
  if ! PYTHON_BIN="$(command -v "$PYTHON_BIN")"; then
    echo "[changed-matrix] ERROR: Python command was not found." >&2
    exit 2
  fi
elif [[ ! -x "$PYTHON_BIN" ]]; then
  echo "[changed-matrix] ERROR: Python is not executable: $PYTHON_BIN" >&2
  exit 2
fi

MANIFEST="$(mktemp "${TMPDIR:-/tmp}/trackify-changed-cases.XXXXXX")"
trap 'rm -f "$MANIFEST"' EXIT

refresh_manifest() {
  "$PYTHON_BIN" "$ROOT_DIR/scripts/sync_engine.py" \
    --list-changed \
    --input "$INPUT_PATH" >"$MANIFEST"
}

manifest_count() {
  "$PYTHON_BIN" -c \
    'import json, sys; print(len(json.load(open(sys.argv[1]))[sys.argv[2]]))' \
    "$MANIFEST" "$1"
}

print_manifest() {
  "$PYTHON_BIN" -c '
import json, sys
payload = json.load(open(sys.argv[1]))
print("[changed-matrix] Pending changes: {}; runnable: {}".format(
    len(payload["changes"]), len(payload["runnable"])
))
for item in payload["changes"]:
    suffix = " -> {}".format(item["nodeid"]) if item["nodeid"] else ""
    print("  - {}: {} ({}){}".format(
        item["kind"], item["test_case_id"], item["title"], suffix
    ))
' "$MANIFEST"
}

refresh_manifest
TOTAL_CHANGES="$(manifest_count changes)"
RUNNABLE_CHANGES="$(manifest_count runnable)"
print_manifest

if [[ "$TOTAL_CHANGES" -eq 0 ]]; then
  echo "[changed-matrix] HEALTHY: registry and Features are already in sync; no changed cases require execution."
  exit 0
fi

MATRIX_ARGS=(
  --env "$ENVIRONMENT"
  --platform "$PLATFORM"
  --distribution replicate
  --appium-url "$APPIUM_URL"
  --android-app "$ANDROID_APP"
  --ios-app "$IOS_APP"
  --report-root "$REPORT_ROOT"
  --change-manifest "$MANIFEST"
  --python "$PYTHON_BIN"
)
if [[ -n "$IOS_REAL_APP" ]]; then
  MATRIX_ARGS+=(--ios-real-app "$IOS_REAL_APP")
fi
if [[ ${#DEVICE_ARGS[@]} -gt 0 ]]; then
  MATRIX_ARGS+=("${DEVICE_ARGS[@]}")
fi

if [[ "$RUNNABLE_CHANGES" -gt 0 ]]; then
  echo "[changed-matrix] Preflight: discovering selected devices."
  "$PYTHON_BIN" "$ROOT_DIR/scripts/run_device_matrix.py" \
    "${MATRIX_ARGS[@]}" --list

  if ! "$PYTHON_BIN" - "$APPIUM_URL" <<'PY'
import sys

from scripts.run_device_matrix import check_appium

try:
    check_appium(sys.argv[1])
except RuntimeError as exc:
    print(f"[changed-matrix] ERROR: {exc}", file=sys.stderr)
    raise SystemExit(2) from exc
PY
  then
    exit 2
  fi

  # Refresh after preflight so the applied and executed selection is current.
  refresh_manifest
  TOTAL_CHANGES="$(manifest_count changes)"
  RUNNABLE_CHANGES="$(manifest_count runnable)"
  if [[ "$TOTAL_CHANGES" -eq 0 ]]; then
    echo "[changed-matrix] HEALTHY: no pending changes remain after preflight."
    exit 0
  fi
fi

echo "[changed-matrix] Applying validated Excel changes."
"$PYTHON_BIN" "$ROOT_DIR/scripts/sync_engine.py" \
  --apply \
  --input "$INPUT_PATH"

if [[ "$RUNNABLE_CHANGES" -eq 0 ]]; then
  echo "[changed-matrix] HEALTHY: lifecycle-only changes applied; no active added/modified cases require execution."
  exit 0
fi

NODEIDS=()
while IFS= read -r nodeid; do
  if [[ -n "$nodeid" ]]; then
    NODEIDS+=("$nodeid")
  fi
done < <(
  "$PYTHON_BIN" -c '
import json, sys
for item in json.load(open(sys.argv[1]))["runnable"]:
    print(item["nodeid"])
' "$MANIFEST"
)

echo "[changed-matrix] Running ${#NODEIDS[@]} changed case(s) on every selected device."
set +e
"$PYTHON_BIN" "$ROOT_DIR/scripts/run_device_matrix.py" \
  "${MATRIX_ARGS[@]}" -- "${NODEIDS[@]}"
MATRIX_STATUS=$?
set -e

case "$MATRIX_STATUS" in
  0)
    echo "[changed-matrix] HEALTHY: all added/modified cases passed on every selected device."
    ;;
  1)
    echo "[changed-matrix] UNHEALTHY: at least one added/modified case failed on at least one device." >&2
    ;;
  *)
    echo "[changed-matrix] ERROR: changed-case matrix could not complete." >&2
    ;;
esac

exit "$MATRIX_STATUS"
