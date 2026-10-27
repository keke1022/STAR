#!/usr/bin/env bash
set -euo pipefail

proof_dir=$(cd "$(dirname "$0")" && pwd)
cbmc_bin=${CBMC_BIN:-cbmc}
common=(
  "$proof_dir/harness.cpp"
  --cpp11
  --bounds-check
  --pointer-check
  --signed-overflow-check
  --unsigned-overflow-check
  --conversion-check
  --div-by-zero-check
)

echo "[1/2] proving all-value equivalence of the production candidate"
"$cbmc_bin" "${common[@]}"

echo "[2/2] requiring a counterexample for a deliberately wrong candidate"
mutant_log=$(mktemp)
trap 'rm -f "$mutant_log"' EXIT
set +e
"$cbmc_bin" "${common[@]}" -DMEDIAN_UINT2_MUTANT --trace >"$mutant_log" 2>&1
mutant_status=$?
set -e
if [[ $mutant_status -eq 0 ]] || ! grep -q 'VERIFICATION FAILED' "$mutant_log"; then
  cat "$mutant_log"
  echo "mutant validation failed: CBMC did not reject the injected bug" >&2
  exit 1
fi
grep -E 'Violated property|actual==expected|VERIFICATION FAILED' "$mutant_log" || true
echo "PASS: all 2^128 input pairs proved equivalent; injected bug rejected"
