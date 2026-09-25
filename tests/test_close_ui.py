import contextlib
import importlib.util
import io
import json
from importlib.machinery import SourceFileLoader
from pathlib import Path
import unittest
from unittest import mock

import close_profile
import dual
import shortcut


class CloseUITests(unittest.TestCase):
    def wrapper(self):
        path = Path(shortcut.__file__).with_name("desktop_close.pyw")
        spec = importlib.util.spec_from_loader("close_wrapper_test", SourceFileLoader("close_wrapper_test", str(path)))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_registered_profile_resolves_exact_electron_path(self):
        target = str(Path(__file__).resolve().parent / "synthetic-profile")
        config = {"profiles": {"alt": {"user_data": target}}}
        with mock.patch.object(dual, "load", return_value=config), \
                mock.patch.object(close_profile.process_control, "plan_close", return_value={}) as plan:
            close_profile.make_plan("alt", None)
        plan.assert_called_once_with(target, exe=None)
        with self.assertRaises(dual.DualError):
            close_profile.make_plan("alt", target)

    def test_cli_preview_never_applies_and_reports_partial_failure(self):
        with mock.patch.object(close_profile, "make_plan", return_value={"processes": [{"pid": 12}]}), \
                mock.patch.object(close_profile.process_control, "apply_close", return_value={"status": "partial"}) as apply, \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(close_profile.main(["alt"]), 0)
            self.assertIn("Save work", output.getvalue())
            apply.assert_not_called()
            self.assertEqual(close_profile.main(["alt", "--apply"]), 1)
            apply.assert_called_once()

    def test_windowless_close_requires_confirmation_and_is_cancellable(self):
        module = self.wrapper()
        plan = {"processes": [{"pid": 12}]}
        with mock.patch.object(module.close_profile, "make_plan", return_value=plan), \
                mock.patch.object(module.process_control, "apply_close", return_value={"status": "closed"}) as apply, \
                mock.patch.object(module.ctypes, "windll", create=True) as windll:
            box = windll.user32.MessageBoxW
            box.return_value = 7
            self.assertEqual(module.main(["alt"]), 0)
            apply.assert_not_called()
            self.assertEqual(box.call_args.args[-1], 0x134)
            self.assertIn("not a graceful", box.call_args.args[1])
            box.return_value = 6
            self.assertEqual(module.main(["alt"]), 0)
            apply.assert_called_once_with(plan)

    def test_no_identified_instance_is_never_terminated(self):
        module = self.wrapper()
        with mock.patch.object(module.close_profile, "make_plan", return_value={"processes": []}), \
                mock.patch.object(module.process_control, "apply_close") as apply, \
                mock.patch.object(module.ctypes, "windll", create=True):
            self.assertEqual(module.main(["alt"]), 0)
            apply.assert_not_called()

    def test_partial_stop_displays_survivors_without_relying_on_new_preview(self):
        module = self.wrapper()
        with mock.patch.object(module.close_profile, "make_plan", return_value={"processes": [{"pid": 12}]}), \
                mock.patch.object(module.process_control, "apply_close", return_value={
                    "status": "partial", "surviving_pids": [34],
                    "failures": [{"error": "Child could not be stopped"}]}), \
                mock.patch.object(module.ctypes, "windll", create=True) as windll:
            windll.user32.MessageBoxW.return_value = 6
            self.assertEqual(module.main(["alt"]), 1)
            message = windll.user32.MessageBoxW.call_args.args[1]
            self.assertIn("34", message)
            self.assertIn("Child could not be stopped", message)


if __name__ == "__main__":
    unittest.main()
