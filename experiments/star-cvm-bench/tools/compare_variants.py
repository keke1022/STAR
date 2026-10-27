#!/usr/bin/env python3
"""Compare upstream and explicitly declared optimized STAR batches.

The environment, workload inputs, index and timed-run shape must match. Binary,
build-flag and STAR-argument changes are rejected unless the caller opts into
each changed dimension. Every raw output signature is recomputed.
"""
import argparse
import json
from pathlib import Path
import sys

from compare_batches import inspect_batch


def compare_variants(baseline, optimized, environment, optimized_variant,
                     minimum=5, baseline_variant="upstream", allow_binary_change=False,
                     allow_build_flags_change=False, allow_star_args_change=False):
    if not baseline_variant or not optimized_variant or optimized_variant == baseline_variant:
        raise ValueError("baseline and optimized variants must be distinct nonempty labels")
    base, bsig, bdata = inspect_batch(baseline, environment, minimum, baseline_variant)
    opt, osig, odata = inspect_batch(optimized, environment, minimum, optimized_variant)

    for key in ("runner_sha256", "threads", "warmups", "repetitions",
                "cache_policy", "profiling"):
        if base.get(key) != opt.get(key):
            raise ValueError("Batch metadata differs: " + key)
    for key in ("workload_id", "source_revision", "input_provenance", "input_kind"):
        if base["config"].get(key) != opt["config"].get(key):
            raise ValueError("Workload differs: " + key)
    if base["config"].get("gzip_reads", False) != opt["config"].get("gzip_reads", False):
        raise ValueError("Workload differs: gzip_reads")

    base_keys, opt_keys = set(base["fingerprints"]), set(opt["fingerprints"])
    if base_keys != opt_keys or "star" not in base_keys:
        raise ValueError("Fingerprint set differs or lacks STAR binary")
    for key in sorted(base_keys - {"star"}):
        if base["fingerprints"][key] != opt["fingerprints"][key]:
            raise ValueError("Input or index fingerprint differs: " + key)

    changes = {}
    dimensions = (
        ("binary", base["fingerprints"]["star"], opt["fingerprints"]["star"], allow_binary_change),
        ("build_flags", base["config"].get("build_flags"), opt["config"].get("build_flags"),
         allow_build_flags_change),
        ("star_args", base["config"].get("star_args", []), opt["config"].get("star_args", []),
         allow_star_args_change),
    )
    for name, before, after, allowed in dimensions:
        if before != after:
            if not allowed:
                raise ValueError(f"{name} differs without explicit allowance")
            changes[name] = {"baseline": before, "optimized": after}
    if not changes:
        raise ValueError("No declared optimization difference found")
    if bsig != osig:
        raise ValueError("Baseline/optimized alignment, statistics or junction output differs")

    ratio = odata["median_seconds"] / bdata["median_seconds"]
    return {
        "status": "PASS",
        "scope": "declared optimization differences and recomputed output equality",
        "environment_verified": False,
        "interpretation": "paired batch comparison; not an isolated cause attribution",
        "environment": environment,
        "threads": base["threads"],
        "baseline_variant": baseline_variant,
        "optimized_variant": optimized_variant,
        "declared_changes": changes,
        "baseline": bdata,
        "optimized": odata,
        "optimized_over_baseline_median_ratio": ratio,
        "observed_relative_time_change": ratio - 1,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline")
    parser.add_argument("optimized")
    parser.add_argument("--environment", required=True,
                        choices=["native-smoke", "vm", "snp", "tdx"])
    parser.add_argument("--baseline-variant", default="upstream")
    parser.add_argument("--optimized-variant", required=True)
    parser.add_argument("--minimum-repetitions", type=int, default=5)
    parser.add_argument("--allow-binary-change", action="store_true")
    parser.add_argument("--allow-build-flags-change", action="store_true")
    parser.add_argument("--allow-star-args-change", action="store_true")
    args = parser.parse_args()
    try:
        result = compare_variants(
            args.baseline, args.optimized, args.environment, args.optimized_variant,
            args.minimum_repetitions, args.baseline_variant, args.allow_binary_change,
            args.allow_build_flags_change, args.allow_star_args_change)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
