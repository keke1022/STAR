import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('fastq', Path(__file__).parents[1] / 'tools/validate_fastq.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class Fastq(unittest.TestCase):
    def test_pairs_and_malformed_inputs(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d)/'a', Path(d)/'b'
            a.write_text('@r/1\nACGT\n+\nIIII\n')
            b.write_text('@r/2\nACGT\n+\nIIII\n')
            self.assertEqual(m.validate(a, b, 1), 1)
            for bad in ('', '@other/2\nACGT\n+\nIIII\n', '@r/2\nACGT\n+\nIII\n'):
                b.write_text(bad)
                with self.assertRaises(ValueError): m.validate(a, b, 1)

    def test_prefix_count_enforced(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a'; a.write_text('@r\nACGT\n+\nIIII\n')
            with self.assertRaises(ValueError): m.validate(a, a, 2)
