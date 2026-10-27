import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/star_bench.py"
spec = importlib.util.spec_from_file_location("bench", SCRIPT)
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)
ROW = "r1\t0\tchr1\t10\t255\t4M\t*\t0\t0\tACGT\tIIII\tNH:i:1\tAS:i:4"


def output(directory, rows, reads=1, pg="A"):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "Aligned.out.sam").write_text(
        "@HD\tVN:1.4\tSO:unsorted\n@SQ\tSN:chr1\tLN:1000\n@PG\tID:" + pg + "\n" + "\n".join(rows) + "\n")
    (directory / "Log.final.out").write_text(
        f"Started job on | variable timestamp\nNumber of input reads | {reads}\nUniquely mapped reads number | {reads}\nMapping speed, Million of reads per hour | 99.9\n")


class Correctness(unittest.TestCase):
    def test_reordering_tags_records_and_pg_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a", Path(tmp) / "b"
            other = ROW.replace("r1\t", "r2\t")
            output(a, [ROW, other], 2)
            output(b, [other, ROW.replace("NH:i:1\tAS:i:4", "AS:i:4\tNH:i:1")], 2, "B")
            for d, command in ((a, "first"), (b, "second")):
                p = d / "Aligned.out.sam"
                p.write_text("@CO\tuser command line: " + command + "\n" + p.read_text())
            for d, timestamp in ((a, "Oct 25 10:00:00"), (b, "Oct 25 10:01:00")):
                p = d / "Log.final.out"
                p.write_text(p.read_text().replace("variable timestamp", timestamp)
                             + "Started mapping on | " + timestamp + "\nFinished on | " + timestamp + "\n")
            self.assertEqual(bench.result_signature(a), bench.result_signature(b))

    def test_semantic_changes_duplicates_and_reference_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a", Path(tmp) / "b"
            output(a, [ROW])
            for changed in (ROW.replace("\t10\t", "\t11\t"), ROW.replace("4M", "2M1I1M"),
                            ROW.replace("NH:i:1", "NH:i:2")):
                output(b, [changed])
                self.assertNotEqual(bench.result_signature(a), bench.result_signature(b))
            output(b, [ROW, ROW])
            self.assertNotEqual(bench.result_signature(a), bench.result_signature(b))
            output(b, [ROW])
            sam = b / "Aligned.out.sam"
            sam.write_text(sam.read_text().replace("LN:1000", "LN:999"))
            self.assertNotEqual(bench.result_signature(a), bench.result_signature(b))

    def test_missing_or_zero_input_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            with self.assertRaises(ValueError):
                bench.result_signature(d)
            output(d, [], 0)
            with self.assertRaises(ValueError):
                bench.result_signature(d)
            output(d, [], 1)
            with self.assertRaises(ValueError):
                bench.result_signature(d)

    def test_paired_mode_rejects_split_qname_groups(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            mate = ROW.replace("\t0\t", "\t128\t", 1)
            other = ROW.replace("r1\t", "r2\t")
            output(d, [ROW, other, mate], 2)
            with self.assertRaisesRegex(ValueError, "not contiguous"):
                bench.result_signature(d)

    def test_paired_mode_rejects_interleaved_multimapper_mates(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            def paired(flag, pos, hi):
                return (ROW.replace("\t0\tchr1\t10\t", f"\t{flag}\tchr1\t{pos}\t")
                        + f"\tHI:i:{hi}")
            left1, right1 = paired(99, 10, 1), paired(147, 20, 1)
            left2, right2 = paired(355, 30, 2), paired(403, 40, 2)
            output(d, [left1, left2, right1, right2])
            with self.assertRaisesRegex(ValueError, "not adjacent"):
                bench.result_signature(d)

    def test_paired_keep_input_order_preserves_group_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a", Path(tmp) / "b"
            other = ROW.replace("r1\t", "r2\t")
            output(a, [ROW, other], 2)
            output(b, [other, ROW], 2)
            command = ["STAR", "--outSAMorder", "PairedKeepInputOrder"]
            (a / "command.json").write_text(json.dumps(command))
            (b / "command.json").write_text(json.dumps(command))
            self.assertNotEqual(bench.result_signature(a), bench.result_signature(b))

    def test_compare_process_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a", Path(tmp) / "b"
            output(a, [ROW]); output(b, [ROW.replace("AS:i:4", "AS:i:3")])
            p = subprocess.run([sys.executable, str(SCRIPT), "compare", str(a), str(b)], capture_output=True)
            self.assertEqual(p.returncode, 1)


class Runner(unittest.TestCase):
    def run_fake(self, body, options=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = root / "STAR"
            fake.write_text("#!/usr/bin/env python3\nimport sys,time\nfrom pathlib import Path\n" + body)
            fake.chmod(0o700)
            genome = root / "index"; genome.mkdir(); (genome / "Genome").write_text("ACGT")
            reads = root / "reads.fq"; reads.write_text("@r1\nACGT\n+\nIIII\n")
            config = {"star": str(fake), "genome_dir": str(genome), "reads": [str(reads)],
                      "workload_id": "test", "source_revision": "fake-test", "build_flags": "test",
                      "input_provenance": "unit-test", "input_kind": "synthetic-smoke"}
            if options and "star_args" in options:
                config["star_args"] = options["star_args"]
            (root / "config.json").write_text(json.dumps(config))
            cmd = [sys.executable, str(SCRIPT), "run", "--config", str(root / "config.json"),
                   "--out", str(root / "out"), "--environment", "native-smoke",
                   "--warmups", "0", "--repetitions", "2", "--timeout", "1"]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            summaries = list((root / "out").glob("summary.json"))
            return proc, [json.loads(p.read_text()) for p in summaries]

    def test_failed_process_missing_output_and_timeout_do_not_pass(self):
        for body in ("sys.exit(3)\n", "sys.exit(0)\n", "time.sleep(5)\n"):
            proc, summaries = self.run_fake(body)
            self.assertNotEqual(proc.returncode, 0, proc.stdout)
            self.assertEqual(summaries, [])

    def test_override_cannot_evade_output_validation(self):
        proc, summaries = self.run_fake("sys.exit(0)\n", {"star_args": ["--outSAMtype", "None"]})
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(summaries, [])

    def test_successful_repeat_and_manifest(self):
        body = ("p=Path(sys.argv[sys.argv.index('--outFileNamePrefix')+1])\n"
                f"(p/'Aligned.out.sam').write_text({(ROW + chr(10))!r})\n"
                "(p/'Log.final.out').write_text('Number of input reads | 1\\n')\n")
        proc, summaries = self.run_fake(body)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(summaries[0]["samples_seconds"]), 2)


if __name__ == "__main__":
    unittest.main()
