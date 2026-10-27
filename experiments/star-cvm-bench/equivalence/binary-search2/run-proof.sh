#!/usr/bin/env bash
set -euo pipefail

proof_dir=$(cd "$(dirname "$0")" && pwd)
cbmc_bin=${CBMC_BIN:-cbmc}
proof_max_n=${PROOF_MAX_N:-8}
unwind=$((proof_max_n + 2))

common=(
  "$proof_dir/harness.cpp"
  --cpp11
  -I "$proof_dir/../../../../source"
  -D"PROOF_MAX_N=$proof_max_n"
  --unwind "$unwind"
  --unwinding-assertions
  --bounds-check
  --pointer-check
  --signed-overflow-check
  --unsigned-overflow-check
  --conversion-check
  --div-by-zero-check
)

echo "[1/2] proving production candidate equivalent to the fb477c5 reference"
"$cbmc_bin" "${common[@]}"

echo "[2/2] requiring a counterexample for a deliberately wrong candidate"
mutant_log=$(mktemp)
trap 'rm -f "$mutant_log"' EXIT
set +e
"$cbmc_bin" "${common[@]}" -DBINARY_SEARCH2_MUTANT --trace >"$mutant_log" 2>&1
mutant_status=$?
set -e
if [[ $mutant_status -eq 0 ]] || ! grep -q 'VERIFICATION FAILED' "$mutant_log"; then
  cat "$mutant_log"
  echo "mutant validation failed: CBMC did not reject the injected bug" >&2
  exit 1
fi
grep -E 'Violated property|actual==expected|VERIFICATION FAILED' "$mutant_log" || true
echo "PASS: equivalence proved within the declared bound; injected bug rejected"
