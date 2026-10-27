import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
from compare_variants import compare_variants
from test_batches import batch, write


class Variants(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.base, self.opt = root / "base", root / "opt"
        batch(self.base, "vm")
        batch(self.opt, "vm")
        path = self.opt / "manifest.json"
        manifest = json.loads(path.read_text())
        manifest["variant"] = "znver5-lto-balanced-io"
        manifest["fingerprints"]["star"]["sha256"] = "optimized-binary"
        manifest["config"]["build_flags"] = "-march=native -flto"
        manifest["config"]["star_args"] = ["--limitIObufferSize", "4000000", "50000000"]
        write(path, manifest)

    def compare(self, **kwargs):
        return compare_variants(
            self.base, self.opt, "vm", "znver5-lto-balanced-io",
            baseline_variant="upstream",
            allow_binary_change=kwargs.get("allow_binary_change", True),
            allow_build_flags_change=kwargs.get("allow_build_flags_change", True),
            allow_star_args_change=kwargs.get("allow_star_args_change", True))

    def test_declared_changes_and_equal_outputs_pass(self):
        result = self.compare()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(set(result["declared_changes"]), {"binary", "build_flags", "star_args"})

    def test_each_changed_dimension_requires_explicit_allowance(self):
        for flag in ("allow_binary_change", "allow_build_flags_change", "allow_star_args_change"):
            with self.assertRaises(ValueError):
                self.compare(**{flag: False})

    def test_input_index_source_and_output_changes_are_rejected(self):
        path = self.opt / "manifest.json"
        original = json.loads(path.read_text())
        cases = []
        for target, key in (("fingerprints", "read0"), ("fingerprints", "index/Genome")):
            changed = copy.deepcopy(original)
            changed[target][key]["sha256"] = "different"
            cases.append(changed)
        changed = copy.deepcopy(original)
        changed["config"]["source_revision"] = "different"
        cases.append(changed)
        for changed in cases:
            write(path, changed)
            with self.assertRaises(ValueError):
                self.compare()

        write(path, original)
        sam = self.opt / "run/4/Aligned.out.sam"
        sam.write_text(sam.read_text().replace("AS:i:4", "AS:i:3"))
        with self.assertRaises(ValueError):
            self.compare()


if __name__ == "__main__":
    unittest.main()
