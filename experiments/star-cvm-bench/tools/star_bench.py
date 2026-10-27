#!/usr/bin/env python3
"""Small, fail-closed STAR alignment runner. No privileged changes or cloud writes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import statistics
import subprocess
import sys
import tempfile
import time


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def multiset_digest(rows):
    """External sort bounds memory, preserves multiplicity, ignores row order."""
    with tempfile.TemporaryDirectory(prefix="star-compare-") as tmp:
        src, dst = Path(tmp) / "rows", Path(tmp) / "sorted"
        count = 0
        with src.open("w") as f:
            for row in rows:
                f.write(hashlib.sha256(row.encode()).hexdigest() + "\n")
                count += 1
        subprocess.run(["sort", "-S", "32M", "-T", tmp, "-o", str(dst), str(src)],
                       env={**os.environ, "LC_ALL": "C"}, check=True)
        return {"count": count, "sha256": sha256(dst)}


def sam_output_order(run_dir):
    command_path = Path(run_dir) / "command.json"
    if not command_path.exists():
        return "Paired"  # STAR 2.7.11b default; also the conservative test-fixture default.
    command = json.loads(command_path.read_text())
    order = "Paired"
    for i, value in enumerate(command):
        if value == "--outSAMorder":
            if i + 1 >= len(command):
                raise ValueError("Missing value for --outSAMorder")
            order = command[i + 1]
        elif value.startswith("--outSAMorder="):
            order = value.split("=", 1)[1]
    if order not in {"Paired", "PairedKeepInputOrder", "Standard"}:
        raise ValueError("Unsupported outSAMorder for validation: " + order)
    return order


def sam_digest(path, output_order="Paired"):
    headers = []
    def resolved_mate_reference(row):
        return row[2] if row[6] == "=" else row[6]

    def validate_adjacent_mates(rows):
        fields = [row.split("\t") for row in rows]
        flags = [int(row[1]) for row in fields]
        if not any(flag & 0x1 for flag in flags):
            return
        if not all(flag & 0x1 for flag in flags) or len(rows) % 2:
            raise ValueError("Paired SAM QNAME group lacks complete adjacent mate units")
        for i in range(0, len(rows), 2):
            left, right = fields[i], fields[i + 1]
            lf, rf = flags[i], flags[i + 1]
            if bool(lf & 0x40) == bool(rf & 0x40) or bool(lf & 0x80) == bool(rf & 0x80):
                raise ValueError("Paired SAM mate records are not adjacent")
            # HI identifies multi-mapping pairs when present, but it is optional
            # in SAM.  The mandatory mate-link fields must therefore agree too:
            # each record's RNEXT/PNEXT must point back to its adjacent mate.
            try:
                left_pnext, right_pnext = int(left[7]), int(right[7])
            except ValueError as exc:
                raise ValueError("Invalid SAM mate position") from exc
            if (resolved_mate_reference(left) != right[2]
                    or resolved_mate_reference(right) != left[2]
                    or left_pnext != int(right[3])
                    or right_pnext != int(left[3])):
                raise ValueError("Adjacent SAM records have inconsistent mate links")
            left_hi = next((tag for tag in left[11:] if tag.startswith("HI:i:")), None)
            right_hi = next((tag for tag in right[11:] if tag.startswith("HI:i:")), None)
            if left_hi != right_hi:
                raise ValueError("Adjacent SAM mates have different HI tags")

    def normalized_records():
        with Path(path).open() as f:
            for line in f:
                fields = line.rstrip("\n").split("\t")
                if line.startswith("@"):
                    # Program invocation/paths and declared output ordering are provenance,
                    # not alignment content. Keep @SQ, @RG, and other header fields.
                    if fields[0] == "@PG" or line.startswith("@CO\tuser command line: "):
                        continue
                    if fields[0] == "@HD":
                        fields = [v for v in fields if not v.startswith(("SO:", "SS:"))]
                    headers.append("\t".join([fields[0], *sorted(fields[1:])]))
                    continue
                if len(fields) < 11:
                    raise ValueError("Malformed SAM alignment")
                int(fields[1]); int(fields[3]); int(fields[4])
                yield "\t".join(fields[:11] + sorted(fields[11:]))
    if output_order == "Standard":
        result = multiset_digest(normalized_records())
    else:
        # Paired modes require every QNAME's records to remain one contiguous
        # group. Canonicalize records inside each group, but do not let a
        # content-only multiset hide split mates or split multimappers.
        with tempfile.TemporaryDirectory(prefix="star-paired-compare-") as tmp:
            tmp = Path(tmp)
            names_path, groups_path = tmp / "group-names", tmp / "groups"
            record_count = group_count = 0
            current_name, current_rows = None, []
            ordered_hash = hashlib.sha256()
            with names_path.open("w") as names, groups_path.open("w") as groups:
                def flush_group():
                    nonlocal group_count
                    if current_name is None:
                        return
                    validate_adjacent_mates(current_rows)
                    name_hash = hashlib.sha256(current_name.encode()).hexdigest()
                    canonical_rows = (current_rows if output_order == "PairedKeepInputOrder"
                                      else sorted(current_rows))
                    group_hash = hashlib.sha256(("\n".join(canonical_rows) + "\n").encode()).hexdigest()
                    row = name_hash + "\t" + group_hash + "\n"
                    names.write(name_hash + "\n")
                    groups.write(row)
                    ordered_hash.update(row.encode())
                    group_count += 1
                for row in normalized_records():
                    record_count += 1
                    name = row.split("\t", 1)[0]
                    if current_name is None:
                        current_name = name
                    elif name != current_name:
                        flush_group()
                        current_name, current_rows = name, []
                    current_rows.append(row)
                flush_group()
            sorted_names = tmp / "group-names.sorted"
            subprocess.run(["sort", "-T", str(tmp), "-o", str(sorted_names), str(names_path)],
                           env={**os.environ, "LC_ALL": "C"}, check=True)
            previous = None
            with sorted_names.open() as names:
                for name_hash in names:
                    if name_hash == previous:
                        raise ValueError("SAM records for one QNAME are not contiguous")
                    previous = name_hash
            if output_order == "Paired":
                sorted_groups = tmp / "groups.sorted"
                subprocess.run(["sort", "-T", str(tmp), "-o", str(sorted_groups), str(groups_path)],
                               env={**os.environ, "LC_ALL": "C"}, check=True)
                digest = sha256(sorted_groups)
            else:
                digest = ordered_hash.hexdigest()
            result = {"count": record_count, "groups": group_count, "sha256": digest,
                      "output_order": output_order}
    result["headers"] = sorted(headers)
    return result


def result_signature(run_dir, validate_sam_order=True):
    root = Path(run_dir)
    sam = root / "Aligned.out.sam"
    log = root / "Log.final.out"
    if not sam.is_file() or not log.is_file():
        raise ValueError("Missing SAM or completed STAR Log.final.out")
    stats = {}
    for line in log.read_text().splitlines():
        if "|" in line:
            k, v = (x.strip() for x in line.split("|", 1))
            if k not in {"Started job on", "Started mapping on", "Finished on",
                         "Mapping speed, Million of reads per hour"}:
                stats[k] = v
    if int(stats.get("Number of input reads", "0")) <= 0:
        raise ValueError("Missing or empty input-read count")
    output_order = sam_output_order(root) if validate_sam_order else "Standard"
    result = {"sam": sam_digest(sam, output_order), "stats": stats}
    if result["sam"]["count"] == 0:
        raise ValueError("Empty alignment output despite nonempty input and Within mode")
    for name in ("SJ.out.tab", "ReadsPerGene.out.tab"):
        p = root / name
        if p.exists():
            with p.open() as f:
                result[name] = multiset_digest(line.rstrip("\n") for line in f)
        else:
            result[name] = None
    return result


def load_config(path):
    c = json.loads(Path(path).read_text())
    for key in ("star", "genome_dir", "reads", "workload_id", "source_revision",
                "build_flags", "input_provenance", "input_kind"):
        if key not in c:
            raise ValueError("Missing config key: " + key)
    if c["input_kind"] not in ("synthetic-smoke", "real-rnaseq"):
        raise ValueError("input_kind must distinguish synthetic from real reads")
    c["star"] = str(Path(c["star"]).resolve(strict=True))
    c["genome_dir"] = str(Path(c["genome_dir"]).resolve(strict=True))
    if not isinstance(c["reads"], list) or len(c["reads"]) not in (1, 2):
        raise ValueError("reads must contain one or two FASTQ paths")
    c["reads"] = [str(Path(p).resolve(strict=True)) for p in c["reads"]]
    extra = c.get("star_args", [])
    if not isinstance(extra, list) or not all(isinstance(v, str) for v in extra):
        raise ValueError("star_args must be a string array")
    reserved = {"--runThreadN", "--runMode", "--genomeDir", "--readFilesIn",
                "--outFileNamePrefix", "--outTmpDir", "--outSAMtype", "--parametersFiles",
                "--runRNGseed", "--genomeLoad", "--outSAMunmapped", "--readFilesCommand"}
    if any(v.split("=", 1)[0] in reserved for v in extra):
        raise ValueError("star_args overrides a controlled experiment parameter")
    if not isinstance(c.get("gzip_reads", False), bool):
        raise ValueError("gzip_reads must be boolean")
    return c


def host_observation():
    # Deliberately omit hostname, user identity, environment variables and credentials.
    result = {"kernel": platform.release(), "architecture": platform.machine(),
              "cpu_count": os.cpu_count(), "affinity": sorted(os.sched_getaffinity(0)),
              "load_average": os.getloadavg()}
    for name in ("meminfo", "pressure/cpu", "pressure/memory", "pressure/io"):
        p = Path("/proc") / name
        result[name] = p.read_text() if p.exists() else None
    p = Path("/proc/vmstat")
    counters = dict(line.split() for line in p.read_text().splitlines()) if p.exists() else {}
    result["vmstat"] = {key: int(counters[key]) for key in
                        ("pswpin", "pswpout", "pgfault", "pgmajfault") if key in counters}
    result["observed_unix_ns"] = time.time_ns()
    return result


def run(args):
    c = load_config(args.config)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    files = [("star", Path(c["star"]))]
    files += [("read" + str(i), Path(p)) for i, p in enumerate(c["reads"])]
    files += [("index/" + str(p.relative_to(c["genome_dir"])), p)
              for p in sorted(Path(c["genome_dir"]).rglob("*")) if p.is_file()]
    if not (Path(c["genome_dir"]) / "Genome").is_file():
        raise ValueError("No STAR Genome index file")
    fingerprints = {key: {"sha256": sha256(p), "bytes": p.stat().st_size}
                    for key, p in files}
    metadata = {"schema": 2, "runner_sha256": sha256(__file__),
                "config": c, "declared_environment": args.environment,
                "environment_verified": False, "variant": args.variant,
                "cache_policy": "uncontrolled_after_fingerprinting",
                "profiling": "none", "threads": args.threads,
                "warmups": args.warmups, "repetitions": args.repetitions,
                "fingerprints": fingerprints, "host_before": host_observation()}
    write_json(out / "manifest.json", metadata)
    durations, reference, records = [], None, []
    for i in range(args.warmups + args.repetitions):
        warmup = i < args.warmups
        d = out / ("warmup" if warmup else "run") / f"{i:03d}"
        d.mkdir(parents=True)
        cmd = [c["star"], "--runMode", "alignReads", "--runThreadN", str(args.threads),
               "--genomeDir", c["genome_dir"], "--genomeLoad", "NoSharedMemory",
               "--readFilesIn", *c["reads"], "--runRNGseed", "777",
               "--outSAMtype", "SAM", "--outSAMunmapped", "Within",
               "--outFileNamePrefix", str(d) + "/", *c.get("star_args", [])]
        if c.get("gzip_reads", False):
            cmd += ["--readFilesCommand", "zcat"]
        write_json(d / "command.json", cmd)
        observation_before = host_observation()
        started = time.perf_counter()
        with (d / "stdout.txt").open("w") as stdout, (d / "stderr.txt").open("w") as stderr:
            proc = subprocess.Popen(["/usr/bin/time", "-v", "-o", str(d / "time.txt"), *cmd],
                                    stdout=stdout, stderr=stderr,
                                    env={**os.environ, "LC_ALL": "C"}, start_new_session=True)
            try:
                rc = proc.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
                rc = 124
        elapsed = time.perf_counter() - started
        observation_after = host_observation()
        record = {"run": str(d.relative_to(out)), "warmup": warmup,
                  "elapsed_seconds": elapsed, "exit_code": rc,
                  "observation_before": observation_before,
                  "observation_after": observation_after}
        records.append(record)
        write_json(out / "runs.json", records)
        if rc:
            raise ValueError(f"STAR failed (exit {rc}); retained logs in {d}")
        sig = result_signature(d)
        write_json(d / "signature.json", sig)
        if reference is None:
            reference = sig
        elif reference != sig:
            raise ValueError("Alignment/statistics changed between repetitions")
        if not warmup:
            durations.append(elapsed)
    # Correctness hashing and machine observation happen outside timed regions.
    write_json(out / "summary.json", {"status": "PASS", "scope": "process timing and repeatability only",
               "median_seconds": statistics.median(durations), "min_seconds": min(durations),
               "max_seconds": max(durations), "samples_seconds": durations,
               "input_reads": int(reference["stats"]["Number of input reads"]),
               "signature": reference, "host_after": host_observation()})
    print(json.dumps({"status": "PASS", "output": str(out), "median_seconds": statistics.median(durations)}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    r = sub.add_parser("run")
    r.add_argument("--config", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--environment", required=True, choices=["native-smoke", "vm", "snp", "tdx"])
    r.add_argument("--variant", default="upstream")
    r.add_argument("--threads", type=int, default=1)
    r.add_argument("--warmups", type=int, default=1)
    r.add_argument("--repetitions", type=int, default=5)
    r.add_argument("--timeout", type=float, default=3600)
    c = sub.add_parser("compare")
    c.add_argument("left"); c.add_argument("right")
    args = p.parse_args()
    try:
        if args.action == "compare":
            match = result_signature(args.left) == result_signature(args.right)
            print(json.dumps({"alignments_and_statistics_equal": match}))
            return 0 if match else 1
        if min(args.threads, args.repetitions) < 1 or args.warmups < 0 or args.timeout <= 0:
            raise ValueError("Invalid run count, thread count, or timeout")
        run(args)
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
