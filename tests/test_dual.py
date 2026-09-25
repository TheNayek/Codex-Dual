import contextlib
import io
import json
import os
import unittest
import shutil
import uuid
from pathlib import Path
from unittest import mock

import dual


class DualTests(unittest.TestCase):
    def setUp(self):
        self.base = Path(__file__).parent / ("fixture-" + uuid.uuid4().hex)
        self.base.mkdir()
        self.addCleanup(shutil.rmtree, self.base)
        self.config = self.base / "dual.local.json"
        self.patch = mock.patch.object(dual, "CONFIG", self.config)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def invoke(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = dual.main(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def configured(self):
        root = self.base / "profiles"
        self.assertEqual(self.invoke("init", "--root", str(root))[0], 0)
        return root

    def test_init_is_exclusive_and_plan_has_no_side_effects(self):
        root = self.configured()
        self.assertFalse(root.exists())
        original = self.config.read_bytes()
        self.assertNotEqual(self.invoke("init", "--root", str(root))[0], 0)
        exe = self.base / "ChatGPT.exe"
        exe.touch()
        code, output, _ = self.invoke("plan", "alt", "--exe", str(exe), "--", "--flag", "two words")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["argv"], [str(exe), "--flag", "two words"])
        self.assertFalse(root.exists())
        self.assertEqual(self.config.read_bytes(), original)

    def test_add_rejects_overlap_and_main_home(self):
        root = self.configured()
        home = root / "alt" / "home"
        bad = root / "alt" / "home" / "electron"
        self.assertNotEqual(self.invoke("add", "other", "--home", str(home), "--user-data", str(bad))[0], 0)
        main = Path.home() / ".codex"
        self.assertNotEqual(self.invoke("add", "main", "--home", str(main), "--user-data", str(root / "other"))[0], 0)
        self.assertEqual(len(dual.load()["profiles"]), 1)

    def test_register_existing_profile_without_touching_auth(self):
        self.configured()
        external = self.base / "previous-install"
        home = external / "home"
        data = external / "electron"
        home.mkdir(parents=True)
        data.mkdir()
        auth = home / "auth.json"
        auth.write_bytes(b"synthetic-sentinel")
        self.assertEqual(self.invoke("add", "work", "--home", str(home), "--user-data", str(data))[0], 0)
        self.assertEqual(auth.read_bytes(), b"synthetic-sentinel")
        self.assertEqual(dual.load()["profiles"]["work"]["home"], str(home))

    def test_rejects_symlink_and_traversal(self):
        self.assertRaises(dual.DualError, dual.safe_path, str(self.base / ".." / "escape"))
        target = self.base / "target"
        target.mkdir()
        link = self.base / "link"
        try:
            link.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Creating symlinks unavailable")
        self.assertRaises(dual.DualError, dual.safe_path, str(link / "child"))

    def test_child_env_isolated_and_os_env_preserved(self):
        profile = {"home": str(self.base / "h"), "user_data": str(self.base / "d")}
        original = {"PATH": "C:/Tools", "LANG": "en", "CODEX_HOME": "main",
                    "CODEX_ELECTRON_USER_DATA_PATH": "main-data", "CODEX_SECRET": "private",
                    "OPENAI_API_KEY": "private", "AZURE_OPENAI_ENDPOINT": "private"}
        result = dual.clean_env(original, profile)
        self.assertEqual(result["PATH"], "C:/Tools")
        self.assertEqual(result["LANG"], "en")
        self.assertEqual(result["CODEX_HOME"], profile["home"])
        self.assertEqual(result["CODEX_ELECTRON_USER_DATA_PATH"], profile["user_data"])
        self.assertNotIn("CODEX_SECRET", result)
        self.assertNotIn("OPENAI_API_KEY", result)
        self.assertNotIn("AZURE_OPENAI_ENDPOINT", result)
        self.assertEqual(original["CODEX_HOME"], "main")

    def test_launch_passes_argv_and_env_without_shell(self):
        root = self.configured()
        exe = self.base / "ChatGPT.exe"
        exe.touch()
        fake = mock.Mock(pid=123)
        with mock.patch.object(dual.subprocess, "Popen", return_value=fake) as popen:
            code, output, _ = self.invoke("launch", "alt", "--exe", str(exe), "--", "--title", "two words")
        self.assertEqual(code, 0)
        self.assertIn("PID 123", output)
        self.assertEqual(popen.call_args.args[0], [str(exe), "--title", "two words"])
        self.assertFalse(popen.call_args.kwargs["shell"])
        self.assertEqual(popen.call_args.kwargs["env"]["CODEX_HOME"], str(root / "alt" / "home"))
        self.assertTrue((root / "alt" / "electron").is_dir())

    def test_bad_config_types_return_clean_error(self):
        self.config.write_text("{broken", encoding="utf-8")
        code, _, error = self.invoke("doctor")
        self.assertEqual(code, 1)
        self.assertIn("invalid JSON", error)
        for malformed in ([], {}, {"version": 1, "root": str(self.base), "profiles": []},
                          {"version": 1, "root": str(self.base), "profiles": {}},
                          {"version": 1, "root": 42, "profiles": {"alt": {"home": "x", "user_data": "y"}}},
                          {"version": 1, "root": str(self.base), "profiles": {"alt": []}},
                          {"version": 1, "root": str(self.base), "profiles": {"alt": {"home": 2, "user_data": 3}}}):
            with self.subTest(malformed=malformed):
                self.config.write_text(json.dumps(malformed), encoding="utf-8")
                code, _, error = self.invoke("doctor")
                self.assertEqual(code, 1)
                self.assertTrue(error.startswith("dual: "))

    def test_rejects_roots_user_home_and_reserved_names(self):
        self.assertRaises(dual.DualError, dual.safe_path, str(Path(self.base.anchor)))
        self.assertRaises(dual.DualError, dual.safe_path, str(Path.home()))
        self.assertRaises(dual.DualError, dual.safe_path, str(self.base / "name."))
        self.assertRaises(dual.DualError, dual.safe_path, str(self.base / "name "))
        self.assertRaises(dual.DualError, dual.validate_alias, "con")
        if os.name == "nt":
            self.assertRaises(dual.DualError, dual.safe_path, str(self.base / "stream:name"))

    def test_concurrent_save_refuses_overwrite_and_cleans_owned_files(self):
        self.configured()
        data, original = dual.load_with_bytes()
        updated = json.loads(json.dumps(data))
        updated["profiles"]["work"] = {"home": str(self.base / "h"), "user_data": str(self.base / "e")}
        external = original + b" "
        self.config.write_bytes(external)
        self.assertRaises(dual.DualError, dual.save_existing, updated, original)
        self.assertEqual(self.config.read_bytes(), external)
        self.assertEqual(list(self.base.glob("dual.local.json.*")), [])

    def test_save_failure_cleans_only_its_temp_and_lock(self):
        self.configured()
        data, original = dual.load_with_bytes()
        with mock.patch.object(dual.os, "replace", side_effect=OSError("synthetic replace failure")):
            self.assertRaises(OSError, dual.save_existing, data, original)
        self.assertEqual(self.config.read_bytes(), original)
        self.assertEqual(list(self.base.glob("dual.local.json.*")), [])

    def test_cli_returns_child_exit_and_rejects_windows_shim(self):
        self.configured()
        exe = self.base / "codex.exe"
        exe.touch()
        fake = mock.Mock()
        fake.wait.return_value = 7
        with mock.patch.object(dual.subprocess, "Popen", return_value=fake) as popen:
            code, _, _ = self.invoke("launch", "alt", "--surface", "cli", "--exe", str(exe), "--", "--help")
        self.assertEqual(code, 7)
        fake.wait.assert_called_once()
        self.assertFalse(popen.call_args.kwargs["shell"])
        if os.name == "nt":
            shim = self.base / "codex.cmd"
            shim.touch()
            self.assertEqual(self.invoke("plan", "alt", "--surface", "cli", "--exe", str(shim))[0], 1)

    def test_failed_spawn_reports_error(self):
        self.configured()
        exe = self.base / "ChatGPT.exe"
        exe.touch()
        with mock.patch.object(dual.subprocess, "Popen", side_effect=OSError("synthetic spawn failure")):
            code, _, error = self.invoke("launch", "alt", "--exe", str(exe))
        self.assertEqual(code, 1)
        self.assertIn("synthetic spawn failure", error)


if __name__ == "__main__":
    unittest.main()
