import contextlib
import importlib.util
import io
import os
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('gcp_plan', Path(__file__).parents[1] / 'tools/gcp_plan.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ResourceSafety(unittest.TestCase):
    def call(self, *args):
        with patch.dict(os.environ, {'PROJECT': 'test-project', 'RUN_ID': 'test', 'IMAGE': 'ubuntu-example'}, clear=True), patch('sys.argv', ['gcp_plan', *args]), contextlib.redirect_stdout(io.StringIO()):
            return m.main()

    def test_default_plan_has_no_queries_or_mutations(self):
        with patch.object(m, 'query') as q, patch.object(m.subprocess, 'run') as r:
            self.assertEqual(self.call('create'), 0)
            self.assertEqual(self.call('cleanup'), 0)
            q.assert_not_called()
            r.assert_not_called()

    def test_existing_names_block_creation(self):
        with patch.object(m, 'image_check'), patch.object(m, 'resources', return_value={'instances': [], 'disks': [{'name': 'bio-star-vm-test'}]}), patch.object(m.subprocess, 'run') as r:
            with self.assertRaises(ValueError):
                self.call('create', '--execute')
            r.assert_not_called()

    def test_cleanup_prechecks_both_owners(self):
        owned = {'name': 'bio-star-vm-test', 'labels': {'experiment': 'bio-star', 'run': 'test'}}
        unowned = {'name': 'bio-star-snp-test', 'labels': {'experiment': 'other'}}
        with patch.object(m, 'resources', return_value={'instances': [owned, unowned], 'disks': []}), patch.object(m.subprocess, 'run') as r:
            with self.assertRaises(ValueError):
                self.call('cleanup', '--execute')
            r.assert_not_called()

    def test_cleanup_leftovers_fail(self):
        with patch.object(m, 'resources', return_value={'instances': [], 'disks': [{'name': 'bio-star-vm-test'}]}), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.call('verify-clean'), 1)
            self.assertEqual(self.call('cleanup', '--execute'), 1)

    def test_image_feature_required(self):
        with patch.object(m, 'query', return_value={'name': 'ubuntu-example', 'guestOsFeatures': []}):
            with self.assertRaises(ValueError):
                m.image_check('ubuntu-example')


if __name__ == '__main__':
    unittest.main()
