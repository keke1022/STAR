import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
from compare_batches import compare
from star_bench import result_signature
from test_bench import ROW, output


def write(path, value):
    path.write_text(json.dumps(value))


def batch(root, environment):
    root.mkdir()
    manifest = {"schema": 2, "runner_sha256": "frozen-runner", "declared_environment": environment,
                "variant": "upstream", "profiling": "none", "threads": 1,
                "warmups": 0, "repetitions": 5, "cache_policy": "uncontrolled_after_fingerprinting",
                "fingerprints": {"star": {"sha256": "binary"}, "read0": {"sha256": "input"},
                                 "index/Genome": {"sha256": "index"}},
                "config": {key: "test" for key in
                           ("workload_id", "source_revision", "build_flags", "input_provenance", "input_kind")}}
    # Absolute paths may differ across guests without changing the workload.
    manifest["config"]["star"] = "/" + environment + "/STAR"
    records = []
    for i in range(5):
        d = root / "run" / str(i)
        output(d, [ROW])
        before = {"observed_unix_ns": i * 100 + 1, "vmstat": {"pswpin": 10, "pswpout": 20, "pgmajfault": 5}}
        after = copy.deepcopy(before); after["observed_unix_ns"] += 2
        records.append({"run": "run/" + str(i), "warmup": False, "exit_code": 0,
                        "elapsed_seconds": i + 1, "observation_before": before, "observation_after": after})
    write(root / "manifest.json", manifest)
    write(root / "runs.json", records)
    write(root / "summary.json", {"status": "PASS", "samples_seconds": [1, 2, 3, 4, 5],
                                  "signature": result_signature(root / "run/0")})


class Batches(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.vm, self.snp = Path(self.tmp.name) / "vm", Path(self.tmp.name) / "snp"
        batch(self.vm, "vm"); batch(self.snp, "snp")

    def test_equal_workload_paths_may_differ_without_attestation_claim(self):
        result = compare(self.vm, self.snp)
        self.assertEqual(result["snp_over_vm_median_ratio"], 1)
        self.assertFalse(result["environment_verified"])
        self.assertFalse(result["hardware_parity_verified"])

    def test_binary_input_index_and_arguments_mismatch_rejected(self):
        path = self.snp / "manifest.json"
        original = json.loads(path.read_text())
        for key in ("star", "read0", "index/Genome"):
            changed = copy.deepcopy(original)
            changed["fingerprints"][key]["sha256"] = "different"
            write(path, changed)
            with self.assertRaises(ValueError): compare(self.vm, self.snp)
        for key, value in (("star_args", ["--alignIntronMax", "1"]), ("gzip_reads", True)):
            changed = copy.deepcopy(original); changed["config"][key] = value
            write(path, changed)
            with self.assertRaises(ValueError): compare(self.vm, self.snp)

    def test_raw_output_mutation_rejected_despite_unchanged_pass_summary(self):
        output(self.snp / "run/4", [ROW.replace("AS:i:4", "AS:i:3")])
        p = subprocess.run([sys.executable, str(TOOLS / "compare_batches.py"),
                            str(self.vm), str(self.snp)], capture_output=True)
        self.assertEqual(p.returncode, 1)

    def test_failed_incomplete_duplicated_and_nan_records_rejected(self):
        path = self.snp / "runs.json"
        original = json.loads(path.read_text())
        cases = [original[:-1]]
        for key, value in (("exit_code", 1), ("elapsed_seconds", float("nan")), ("run", "run/0")):
            changed = copy.deepcopy(original); changed[-1][key] = value; cases.append(changed)
        for changed in cases:
            write(path, changed)
            with self.assertRaises(ValueError): compare(self.vm, self.snp)

    def test_different_runner_threads_and_environment_rejected(self):
        path = self.snp / "manifest.json"
        original = json.loads(path.read_text())
        for key, value in (("runner_sha256", "changed"), ("threads", 4),
                           ("declared_environment", "native-smoke")):
            changed = copy.deepcopy(original); changed[key] = value
            write(path, changed)
            with self.assertRaises(ValueError): compare(self.vm, self.snp)

    def test_summary_timing_tamper_rejected(self):
        path = self.snp / "summary.json"
        changed = json.loads(path.read_text()); changed["samples_seconds"] = [0.1] * 5
        write(path, changed)
        with self.assertRaises(ValueError): compare(self.vm, self.snp)

    def test_real_runner_artifacts_feed_comparator(self):
        root = Path(self.tmp.name)
        fake = root / "STAR"
        fake.write_text("#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\n"
                        "p=Path(sys.argv[sys.argv.index('--outFileNamePrefix')+1])\n"
                        f"(p/'Aligned.out.sam').write_text({(ROW + chr(10))!r})\n"
                        "(p/'Log.final.out').write_text('Number of input reads | 1\\n')\n")
        fake.chmod(0o700)
        index = root / "index"; index.mkdir(); (index / "Genome").write_text("ACGT")
        reads = root / "read.fq"; reads.write_text("@r1\nACGT\n+\nIIII\n")
        config = root / "config.json"
        write(config, {"star": str(fake), "genome_dir": str(index), "reads": [str(reads)],
                       "workload_id": "test", "source_revision": "test", "build_flags": "test",
                       "input_provenance": "synthetic", "input_kind": "synthetic-smoke"})
        for env in ("vm", "snp"):
            p = subprocess.run([sys.executable, str(TOOLS / "star_bench.py"), "run",
                                "--config", str(config), "--out", str(root / (env + "-actual")),
                                "--environment", env, "--warmups", "1", "--repetitions", "5"],
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
        result = compare(root / "vm-actual", root / "snp-actual")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["vm"]["observations"]), 5)
        self.assertGreater(result["vm"]["observations"][0]["observed_start_unix_ns"], 0)


if __name__ == "__main__":
    unittest.main()
