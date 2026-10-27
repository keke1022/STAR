# STAR local equivalence-proof prototype

Date: 2026-10-27  
Base commit: `fb477c5365cf09a59ca0137b9099c6dcf49ed4a2`  
Branch: `proof/star-local-equivalence`

## Result

The experiment established two different proof levels and, importantly, kept
their scopes separate:

1. `medianUint2` has a complete fixed-width proof.  CBMC proved the new bitwise
   expression equal to the old arithmetic expression for every pair of 64-bit
   unsigned inputs: all `2^128` input pairs.  This function has no external
   state, loops, pointers, or preconditions.
2. `binarySearch2` has a useful but bounded regression proof.  CBMC proved the
   production candidate equal to a byte-for-byte snapshot of the old source for
   every 64-bit query and every strictly lexicographically ordered array with
   `0 <= N <= 8`.  It also proved memory safety, absence of checked arithmetic
   errors, and that neither input array is modified within that bound.  This is
   not a proof for arbitrary array length.

Both harnesses also compile a deliberately wrong implementation.  The proof
scripts pass only if CBMC rejects that mutant with a counterexample.  This
guards against a vacuous assumption or a disconnected assertion.

## Changes under test

### `medianUint2`

Old:

```cpp
return a/2 + b/2 + (a%2 + b%2)/2;
```

Candidate:

```cpp
return (a & b) + ((a ^ b) >> 1);
```

The candidate is in `source/medianUint2.h`, included by the original
`SuffixArrayFuns.cpp` call sites.  With GCC 15.2, `-O3 -fno-inline`, the isolated
old and new bodies compile to ten and five instructions respectively before
`ret` (excluding `endbr64`).  This is a code-generation observation, not an
end-to-end speedup claim.

### `binarySearch2`

The old implementation binary-searches only `X`, then scans linearly across all
equal `X` entries to find `Y`.  The candidate lower-bounds the pair `(X,Y)`,
changing the worst case from `O(log N + equal-X-run)` to `O(log N)`.

The proof exposed an undocumented observable behavior before it accepted the
candidate: when `X` exists but `Y` does not, the old function returns `-2` only
if that `X` run reaches the end of the array; otherwise it returns `-1`.  The
first candidate lost this distinction, and the randomized differential test
failed.  The checked candidate deliberately preserves it.

The candidate relies on a contract now documented in `binarySearch2.h`:

- `N >= 0` and both arrays address at least `N` elements;
- `(X[i],Y[i])` is strictly increasing in lexicographic order, so duplicate
  pairs have been collapsed.

This contract composes with the current STAR producers:

- `sjdbPrepare.cpp` sorts by `funCompareUint2` (first field, then second) and
  collapses duplicate junction pairs before filling `sjdbStart/sjdbEnd`;
- `OutSJ::collapseSJ` sorts by start then gap and collapses duplicates;
- `outputSJ.cpp` takes an order-preserving filtered subset for `sjNovel`, and
  computes end as `start + gap - 1`, preserving the second-key order for equal
  starts.

Any future caller that does not satisfy this precondition invalidates the
composition argument even though the bounded harness still passes.

## Machine-checked scope

Tool:

- CBMC `6.6.0` (`cbmc_6.6.0-4_amd64.deb` from Ubuntu questing);
- package SHA-256:
  `9f36cd1d9234fbec552c1aea811c7a4f44ac0eeb82a462fc93ddcd500273d5f9`;
- MiniSat package SHA-256:
  `5a5b0ca60d614caf9ab4c788e80358c95ce5f14277742f9f0a4e1305cae964ef`.

The local extracted tool was invoked as follows:

```sh
export CBMC_BIN="$PWD/../tools/cbmc-6.6.0/root/usr/bin/cbmc"
export LD_LIBRARY_PATH="$PWD/../tools/cbmc-6.6.0/root/usr/lib"
experiments/star-cvm-bench/equivalence/median-uint2/run-proof.sh
experiments/star-cvm-bench/equivalence/binary-search2/run-proof.sh
```

Observed results:

- `medianUint2`: 0/5 properties failed; `VERIFICATION SUCCESSFUL`; mutant
  assertion failed as required.
- `binarySearch2`, `PROOF_MAX_N=8`: 0/154 properties failed;
  `VERIFICATION SUCCESSFUL`; mutant assertion failed as required.
- The binary-search proof covers all 64-bit element/query values and every
  length from zero through eight, but no length above eight.  Raising
  `PROOF_MAX_N` increases solver cost sharply: an `N<=16` attempt was stopped
  after 6 minutes 43 seconds without a result.  A proof for arbitrary `N` needs
  loop invariants and a deductive/relational verifier, not a larger marketing
  claim about this CBMC run.

The formal reference file is byte-identical to the old production source:

```sh
diff -u \
  <(git show fb477c5:source/binarySearch2.cpp) \
  experiments/star-cvm-bench/equivalence/binary-search2/reference.cpp
```

Its SHA-256 is
`f793e8bca4d26019727865c8145d1018839c34ce41a495787557bf7843217a50`.
The harness directly includes both that snapshot and the current production
`source/binarySearch2.cpp`; it does not prove two detached hand-written models.

## Non-formal validation

- A seeded native differential test generated 20,000 unique sorted arrays with
  up to 256 pairs and issued 100 queries per array (2,000,000 comparisons):
  PASS.
- The full STAR source built successfully with the normal `make -C source -j8
  STAR` target.
- All 29 existing `star-cvm-bench` unit tests passed.
- On the fixed 100,000-pair Drosophila input, old and candidate binaries both
  produced 220,318 SAM records in 100,000 QNAME groups.  Recomputed semantic
  SAM digest was identical:
  `fb972d3530ef69e4231f8540800f7d6b4b548686f4b68f5fc14d1d4a7b303ac1`.
  `SJ.out.tab` SHA-256 was also identical:
  `217609ffc4c25b5de97ebd5d95a680453dd0f6bc045317f9008b286528753728`.

The `binarySearch2` microbenchmark is intentionally adversarial.  With 4,096
distinct `X` values, one million queries, and 1,024 `Y` values per `X`, the
candidate was about 2.05x faster at the median of five runs.  It was about 8%
slower with groups of 16.  The Drosophila index has 60,508 junctions, 53,736
distinct starts, and a maximum equal-start group of 48; therefore this result
does not justify claiming a STAR workload speedup or merging the search change
without a representative benchmark.

The standalone checks can be reproduced from the repository root with:

```sh
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  experiments/star-cvm-bench/equivalence/binary-search2/test_binary_search2.cpp \
  -o /tmp/star-binary-search2-test
/tmp/star-binary-search2-test

g++ -std=c++17 -O3 -march=native -Wall -Wextra -Werror \
  experiments/star-cvm-bench/equivalence/binary-search2/microbench.cpp \
  -o /tmp/star-binary-search2-microbench
/tmp/star-binary-search2-microbench 4096 1024 1000000

python3 -m unittest discover -s experiments/star-cvm-bench/tests \
  -p 'test_*.py' -v
make -C source -j8 STAR
```

## Decision boundary

- The `medianUint2` proof is a genuine all-input local equivalence proof for
  STAR's 64-bit `uint` definition.  It demonstrates that a small source change
  can inherit trust from the old function without testing every input.
- The `binarySearch2` exercise demonstrates bounded regression verification,
  a real counterexample caught during development, and how producer invariants
  must be connected to the function contract.  It must not be described as
  arbitrary-length equivalence.
- Neither result proves whole-program STAR equivalence.  Unchanged STAR code is
  outside these local proof obligations; build, integration, concurrency, and
  caller-contract evidence remain separate.
- The branch is a proof prototype.  `medianUint2` is a reasonable review
  candidate; `binarySearch2` should remain experimental until representative
  workload profiling shows value and an unbounded proof (or an accepted,
  explicit bound tied to all callers) is available.
