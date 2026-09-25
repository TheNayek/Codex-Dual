import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import msix


class MsixTests(unittest.TestCase):
    def test_profile_arguments_remain_data_not_powershell_code(self):
        script = Path(__file__).resolve()
        args = ['--app=codex', 'Profile name; $(unexpected) "quoted"']
        with patch.object(Path, 'is_file', return_value=True):
            payload = msix.bootstrap_payload(script, args)
        self.assertEqual(payload['arguments'], subprocess.list2cmdline([str(script), *args]))
        self.assertNotIn(args[-1], msix._BOOTSTRAP)
        self.assertNotIn('CODEX_HOME', msix._BOOTSTRAP)

    def test_package_bootstrap_reenters_launcher_and_preserves_child_identity(self):
        payload = {'family':msix.PACKAGE_FAMILY,'command':'pythonw.exe','arguments':'launcher.pyw alt'}
        with patch.object(msix, 'bootstrap_payload', return_value=payload), \
             patch.object(msix.subprocess, 'CREATE_NO_WINDOW', 0, create=True), \
             patch.object(msix.subprocess, 'run', return_value=subprocess.CompletedProcess([],0,'','')) as run:
            msix.relaunch_with_package(Path('launcher'), ['alt'])
        self.assertEqual(json.loads(run.call_args.kwargs['input']), payload)
        self.assertFalse(run.call_args.kwargs['shell'])
        self.assertIn('-PreventBreakaway', run.call_args.args[0][-1])

    def test_package_launch_failure_is_reported(self):
        with patch.object(msix, 'bootstrap_payload', return_value={}), \
             patch.object(msix.subprocess, 'CREATE_NO_WINDOW', 0, create=True), \
             patch.object(msix.subprocess, 'run', return_value=subprocess.CompletedProcess([],1,'','failure')):
            with self.assertRaisesRegex(RuntimeError, 'failure'):
                msix.relaunch_with_package(Path('launcher'), [])
