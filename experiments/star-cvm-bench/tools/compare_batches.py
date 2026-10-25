#!/usr/bin/env python3
"""Check matching upstream VM/SNP batches and recompute every output signature.

This verifies recorded workload identity and outputs, not SNP attestation or
hardware equivalence. Timing ratios remain exploratory on a shared host.
"""
import argparse
import json
import math
from pathlib import Path
import statistics
import sys

from star_bench import result_signature


def read_json(path):
    return json.loads(Path(path).read_text())


def inspect_batch(root, environment, minimum):
    root = Path(root).resolve()
    m = read_json(root / "manifest.json")
    records = read_json(root / "runs.json")
    summary = read_json(root / "summary.json")
    if m.get("schema") != 2 or not m.get("runner_sha256"):
        raise ValueError("Batch must use runner schema 2 with its source fingerprint")
    if m.get("declared_environment") != environment or m.get("variant") != "upstream":
        raise ValueError("Expected distinct vm/snp upstream batches")
    if m.get("profiling") != "none" or summary.get("status") != "PASS":
        raise ValueError("Need completed, unprofiled batches")
    if len(records) != m["warmups"] + m["repetitions"] or m["repetitions"] < minimum:
        raise ValueError("Incomplete batch or insufficient timed repetitions")
    samples, seen, signature, observations = [], set(), None, []
    for i, row in enumerate(records):
        warmup = i < m["warmups"]
        if row["warmup"] is not warmup or row["exit_code"] != 0:
            raise ValueError("Failed run or inconsistent warmup accounting")
        duration = row["elapsed_seconds"]
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
            raise ValueError("Invalid measured duration")
        run_dir = (root / row["run"]).resolve()
        if root not in run_dir.parents or run_dir in seen:
            raise ValueError("Duplicate or escaping run directory")
        seen.add(run_dir)
        actual = result_signature(run_dir)  # Do not trust cached PASS/signatures.
        if signature is None:
            signature = actual
        elif actual != signature:
            raise ValueError("Output mismatch inside a batch")
        before, after = row["observation_before"], row["observation_after"]
        if after["observed_unix_ns"] < before["observed_unix_ns"]:
            raise ValueError("Observation clock moved backwards")
        deltas = {}
        for key in ("pswpin", "pswpout", "pgmajfault"):
            a, b = before["vmstat"].get(key), after["vmstat"].get(key)
            if a is None or b is None:
                deltas[key] = None
            elif b < a:
                raise ValueError("System counters moved backwards")
            else:
                deltas[key] = b - a
        if not warmup:
            samples.append(duration)
            observations.append({"system_counter_deltas": deltas,
                                 "observed_start_unix_ns": before["observed_unix_ns"],
                                 "observed_end_unix_ns": after["observed_unix_ns"]})
    if samples != summary["samples_seconds"] or signature != summary["signature"]:
        raise ValueError("Stored summary disagrees with raw runs")
    return m, signature, {"samples_seconds": samples, "median_seconds": statistics.median(samples),
                          "min_seconds": min(samples), "max_seconds": max(samples),
                          "observations": observations}


def compare(vm, snp, minimum=5):
    if minimum < 1:
        raise ValueError("minimum repetitions must be positive")
    left, lsig, ldata = inspect_batch(vm, "vm", minimum)
    right, rsig, rdata = inspect_batch(snp, "snp", minimum)
    for key in ("runner_sha256", "fingerprints", "threads", "warmups", "repetitions",
                "cache_policy", "profiling", "variant"):
        if key not in left or left[key] != right.get(key):
            raise ValueError("Batch metadata differs: " + key)
    for key in ("workload_id", "source_revision", "build_flags", "input_provenance", "input_kind"):
        if left["config"][key] != right["config"].get(key):
            raise ValueError("Workload differs: " + key)
    for key, default in (("gzip_reads", False), ("star_args", [])):
        if left["config"].get(key, default) != right["config"].get(key, default):
            raise ValueError("STAR arguments differ: " + key)
    if not left["fingerprints"] or "star" not in left["fingerprints"] or not any(k.startswith("read") for k in left["fingerprints"]) or "index/Genome" not in left["fingerprints"]:
        raise ValueError("Missing workload fingerprints")
    if lsig != rsig:
        raise ValueError("VM/SNP alignment, statistics or junction output differs")
    ratio = rdata["median_seconds"] / ldata["median_seconds"]
    return {"status": "PASS", "scope": "recorded workload identity and recomputed output equality",
            "environment_verified": False, "hardware_parity_verified": False,
            "interpretation": "exploratory batch ratio; not isolated SNP overhead or a speedup claim",
            "threads": left["threads"], "vm": ldata, "snp": rdata,
            "snp_over_vm_median_ratio": ratio,
            "observed_relative_time_difference": ratio - 1}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vm"); parser.add_argument("snp")
    parser.add_argument("--minimum-repetitions", type=int, default=5)
    args = parser.parse_args()
    try:
        print(json.dumps(compare(args.vm, args.snp, args.minimum_repetitions), indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
