import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import unittest
import uuid
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock

import dual
import shortcut


class ShortcutTests(unittest.TestCase):
    def setUp(self):
        self.base = Path(__file__).parent / ("shortcut-fixture-" + uuid.uuid4().hex)
        self.base.mkdir()
        self.addCleanup(shutil.rmtree, self.base)
        self.desktop = self.base / "Desktop á's space"
        self.desktop.mkdir()
        self.config = self.base / "dual.local.json"
        self.config.write_text(json.dumps({
            "version": 1, "root": str(self.base / "profiles"),
            "profiles": {"alt": {
                "home": str(self.base / "profiles" / "alt" / "home"),
                "user_data": str(self.base / "profiles" / "alt" / "electron"),
            }},
        }), encoding="utf-8")
        patch = mock.patch.object(dual, "CONFIG", self.config)
        patch.start()
        self.addCleanup(patch.stop)
        self.python = self.base / "python.exe"
        self.python.touch()
        self.python.with_name("pythonw.exe").touch()

    def test_plan_uses_windowless_wrapper_without_app_path_or_side_effects(self):
        before = self.config.read_bytes()
        plan = shortcut.build_plan("alt", self.desktop, python_executable=self.python)
        self.assertEqual(plan["target"], str(self.python.with_name("pythonw.exe")))
        self.assertEqual(plan["path"], str(self.desktop / "Codex - alt.lnk"))
        self.assertIn("desktop_launch.pyw", plan["arguments"])
        self.assertNotIn("ChatGPT.exe", json.dumps(plan))
        self.assertEqual(list(self.desktop.iterdir()), [])
        self.assertEqual(self.config.read_bytes(), before)

    def test_refuses_unregistered_alias_and_existing_destination(self):
        with self.assertRaisesRegex(dual.DualError, "Unknown alias"):
            shortcut.build_plan("other", self.desktop, python_executable=self.python)
        target = self.desktop / "Codex - alt.lnk"
        target.write_bytes(b"original")
        with self.assertRaisesRegex(dual.DualError, "already exists"):
            shortcut.build_plan("alt", self.desktop, python_executable=self.python)
        self.assertEqual(target.read_bytes(), b"original")

    def test_refuses_relative_desktop_and_missing_pythonw(self):
        with self.assertRaises(dual.DualError):
            shortcut.build_plan("alt", Path("Desktop"), python_executable=self.python)
        self.python.with_name("pythonw.exe").unlink()
        with self.assertRaisesRegex(dual.DualError, "pythonw.exe"):
            shortcut.build_plan("alt", self.desktop, python_executable=self.python)

    def test_special_characters_in_paths_are_quoted(self):
        special = self.base / "O'Brien 日本語 files"
        special.mkdir()
        (special / "desktop_launch.pyw").write_text("", encoding="utf-8")
        python = special / "python.exe"
        python.with_name("pythonw.exe").touch()
        with mock.patch.object(shortcut, "__file__", str(special / "shortcut.py")):
            plan = shortcut.build_plan("alt", self.desktop, python_executable=python)
        self.assertEqual(plan["target"], str(python.with_name("pythonw.exe")))
        self.assertEqual(plan["arguments"], subprocess.list2cmdline([str(special / "desktop_launch.pyw"), "alt"]))

    @unittest.skipUnless(os.name == "nt", "Windows rename no-overwrite behavior")
    def test_collision_during_publication_preserves_existing_shortcut(self):
        plan = shortcut.build_plan("alt", self.desktop, python_executable=self.python)
        destination = Path(plan["path"])

        def competing_writer(_script, *, input_text):
            temporary = Path(json.loads(input_text)["path"])
            temporary.write_bytes(b"our temporary shortcut")
            destination.write_bytes(b"other process")

        with self.assertRaisesRegex(dual.DualError, "already exists"):
            shortcut.create_shortcut(plan, runner=competing_writer)
        self.assertEqual(destination.read_bytes(), b"other process")
        self.assertEqual(sorted(self.desktop.iterdir()), [destination])

    def test_windowless_wrapper_routes_alias_and_reports_failure(self):
        path = Path(shortcut.__file__).with_name("desktop_launch.pyw")
        spec = importlib.util.spec_from_loader("desktop_launch_test", SourceFileLoader("desktop_launch_test", str(path)))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with mock.patch.object(module.dual, "main", return_value=0) as launch:
            self.assertEqual(module.main(["alt"]), 0)
            launch.assert_called_once_with(["launch", "alt"])
        fake_user32 = mock.Mock()
        with mock.patch.object(module.dual, "main", return_value=1), \
             mock.patch.object(module.ctypes, "windll", create=True) as windll:
            windll.user32 = fake_user32
            self.assertEqual(module.main(["alt"]), 1)
            fake_user32.MessageBoxW.assert_called_once()

    @unittest.skipUnless(os.name == "nt", "Windows COM shortcut integration")
    def test_actual_lnk_in_fixture_desktop(self):
        # Exercise the public --desktop-dir path with the real installed pythonw.
        if not Path(sys.executable).with_name("pythonw.exe").is_file():
            self.skipTest("pythonw.exe unavailable")
        output, error = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            self.assertEqual(shortcut.main(["alt", "--desktop-dir", str(self.desktop)]), 0, error.getvalue())
        self.assertEqual(list(self.desktop.iterdir()), [])
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            self.assertEqual(shortcut.main(["alt", "--desktop-dir", str(self.desktop), "--apply"]), 0, error.getvalue())
        destination = self.desktop / "Codex - alt.lnk"
        self.assertTrue(destination.is_file())
        inspect = r"""
$path = [Console]::In.ReadToEnd()
$link = (New-Object -ComObject WScript.Shell).CreateShortcut($path)
@{ target = $link.TargetPath; arguments = $link.Arguments } | ConvertTo-Json -Compress
"""
        details = json.loads(shortcut._powershell(inspect, input_text=str(destination)))
        self.assertEqual(Path(details["target"]), Path(sys.executable).with_name("pythonw.exe"))
        self.assertIn("desktop_launch.pyw", details["arguments"])
        self.assertTrue(details["arguments"].endswith(" alt"))
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            self.assertEqual(shortcut.main(["alt", "--desktop-dir", str(self.desktop), "--apply"]), 1)
        self.assertTrue(destination.is_file())


if __name__ == "__main__":
    unittest.main()
