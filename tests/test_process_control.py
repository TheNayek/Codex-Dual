"""Synthetic process inventories only; never stop an actual desktop process."""
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

PRODUCT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PRODUCT))
import process_control as pc


PROFILE = r"C:\Fixtures\Secondary Profile"
OTHER = r"C:\Fixtures\Secondary Profile Backup"
EXE = r"C:\Program Files\WindowsApps\Codex\app\ChatGPT.exe"


def inventory(roots, parents):
    if not any(pid == 900 for pid, _ in parents):
        parents = [*parents, (900, 1)]
    return {"roots": [{"pid": pid, "command_line": command} for pid, command in roots],
            "processes": [{"pid": pid, "parent_pid": parent} for pid, parent in parents]}


class SyntheticProcessCase(unittest.TestCase):
    def setUp(self):
        self.patchers = [
            mock.patch.object(pc, "_ensure_windows"),
            mock.patch.object(pc, "_current_pid", return_value=900),
            mock.patch.object(pc, "_open", side_effect=lambda pid, terminate=False: pid),
            mock.patch.object(pc, "_close"),
            mock.patch.object(pc, "_identity", side_effect=lambda handle: (handle * 100, pc._normal_path(EXE) if handle in (10, 20) else r"c:\windows\child.exe")),
            mock.patch.object(pc, "_argv", side_effect=lambda command: command if isinstance(command, list) else (_ for _ in ()).throw(pc.ProcessControlError("Missing command line"))),
        ]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)


class SelectionTests(SyntheticProcessCase):
    def test_quoted_entire_flag_and_primary_excluded(self):
        snapshot = inventory([(10, [EXE, f"--user-data-dir={PROFILE}"]),
                              (20, [EXE])], [(10, 1), (11, 10), (20, 1)])
        with mock.patch.object(pc, "_snapshot", return_value=snapshot):
            plan = pc.plan_close(PROFILE, EXE)
        self.assertEqual(plan["root_pid"], 10)
        self.assertEqual([p["pid"] for p in plan["processes"]], [10, 11])

    def test_similar_path_and_other_root_are_excluded(self):
        snapshot = inventory([(10, [EXE, f"--user-data-dir={PROFILE}"]),
                              (20, [EXE, "--user-data-dir", OTHER])],
                             [(10, 1), (11, 10), (20, 10), (21, 20)])
        with mock.patch.object(pc, "_snapshot", return_value=snapshot):
            plan = pc.plan_close(PROFILE, EXE)
        self.assertEqual([p["pid"] for p in plan["processes"]], [10, 11])

    def test_ambiguous_roots_and_missing_command_line_abort(self):
        for roots in (
            [(10, [EXE, f"--user-data-dir={PROFILE}"]), (20, [EXE, "--user-data-dir", PROFILE])],
            [(10, None)],
            [(10, [EXE, f"--user-data-dir={PROFILE}", "--user-data-dir", OTHER])],
        ):
            with self.subTest(roots=roots), mock.patch.object(pc, "_snapshot", return_value=inventory(roots, [(10, 1), (20, 1)])):
                with self.assertRaises(pc.ProcessControlError):
                    pc.plan_close(PROFILE, EXE)

    def test_child_type_and_parent_pid_reuse_not_selected(self):
        snapshot = inventory([(10, [EXE, f"--user-data-dir={PROFILE}"]),
                              (20, [EXE, "--type=renderer", f"--user-data-dir={PROFILE}"])],
                             [(10, 1), (11, 10), (20, 10)])
        # PID 11 predates its listed parent, so its parent PID has been reused.
        def identity(pid):
            created = {10: 1000, 11: 500, 20: 1100}[pid]
            return created, pc._normal_path(EXE) if pid == 10 else r"c:\windows\child.exe"
        with mock.patch.object(pc, "_identity", side_effect=identity), mock.patch.object(pc, "_snapshot", return_value=snapshot):
            plan = pc.plan_close(PROFILE, EXE)
        self.assertEqual([p["pid"] for p in plan["processes"]], [10, 20])

    def test_calling_process_ancestor_is_protected(self):
        snapshot = inventory([(10, [EXE, f"--user-data-dir={PROFILE}"])],
                             [(10, 1), (900, 10)])
        with mock.patch.object(pc, "_snapshot", return_value=snapshot):
            with self.assertRaisesRegex(pc.ProcessControlError, "calling"):
                pc.plan_close(PROFILE, EXE)

    def test_idle_process_pid_zero_does_not_block_preview(self):
        snapshot = inventory([(10, [EXE, f"--user-data-dir={PROFILE}"])],
                             [(0, 0), (10, 0)])
        with mock.patch.object(pc, "_snapshot", return_value=snapshot):
            plan = pc.plan_close(PROFILE, EXE)
        self.assertEqual([p["pid"] for p in plan["processes"]], [10])


class ApplyTests(SyntheticProcessCase):
    def test_detached_preview_child_remains_visible_as_partial(self):
        preview = inventory([(10, [EXE, f"--user-data-dir={PROFILE}"])],
                            [(10, 1), (11, 10), (12, 11)])
        detached = inventory([(10, [EXE, f"--user-data-dir={PROFILE}"])],
                             [(10, 1), (12, 11)])
        with mock.patch.object(pc, "_snapshot", return_value=preview):
            plan = pc.plan_close(PROFILE, EXE)
        live = {10, 12}
        def terminate(_, pid):
            live.remove(pid)
        with mock.patch.object(pc, "_snapshot", return_value=detached), \
             mock.patch.object(pc, "_alive", side_effect=lambda handle: handle in live), \
             mock.patch.object(pc, "_terminate", side_effect=terminate) as stop, \
             mock.patch.object(pc, "_wait"):
            result = pc.apply_close(plan)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["surviving_pids"], [12])
        self.assertEqual(result["terminated_pids"], [10])
        self.assertEqual({call.args[1] for call in stop.call_args_list}, {10})

    def test_apply_terminates_only_selected_pinned_tree(self):
        snapshot = inventory([(10, [EXE, f"--user-data-dir={PROFILE}"]), (20, [EXE])],
                             [(10, 1), (11, 10), (20, 1)])
        with mock.patch.object(pc, "_snapshot", return_value=snapshot):
            plan = pc.plan_close(PROFILE, EXE)
        live = {10, 11, 20}
        def terminate(_, pid):
            live.remove(pid)
        with mock.patch.object(pc, "_snapshot", return_value=snapshot), \
             mock.patch.object(pc, "_alive", side_effect=lambda handle: handle in live), \
             mock.patch.object(pc, "_terminate", side_effect=terminate) as stop, \
             mock.patch.object(pc, "_wait"):
            result = pc.apply_close(plan)
        self.assertEqual(result["status"], "closed")
        self.assertEqual(set(result["terminated_pids"]), {10, 11})
        self.assertEqual(live, {20})
        self.assertEqual({call.args[1] for call in stop.call_args_list}, {10, 11})

    def test_pid_reuse_aborts_before_any_termination(self):
        snapshot = inventory([(10, [EXE, f"--user-data-dir={PROFILE}"])], [(10, 1), (11, 10)])
        with mock.patch.object(pc, "_snapshot", return_value=snapshot):
            plan = pc.plan_close(PROFILE, EXE)
        changed = dict(plan)
        changed["processes"] = [dict(item) for item in plan["processes"]]
        changed["processes"][1]["created"] -= 1
        with mock.patch.object(pc, "_snapshot", return_value=snapshot), mock.patch.object(pc, "_terminate") as terminate:
            with self.assertRaisesRegex(pc.ProcessControlError, "changed identity"):
                pc.apply_close(changed)
            terminate.assert_not_called()

    def test_pinned_identity_recheck_aborts_before_any_termination(self):
        snapshot = inventory([(10, [EXE, f"--user-data-dir={PROFILE}"])], [(10, 1)])
        with mock.patch.object(pc, "_snapshot", return_value=snapshot):
            plan = pc.plan_close(PROFILE, EXE)
        calls = iter([(1000, pc._normal_path(EXE)), (1001, pc._normal_path(EXE))])
        with mock.patch.object(pc, "_snapshot", return_value=snapshot), mock.patch.object(pc, "_identity", side_effect=lambda _: next(calls)), mock.patch.object(pc, "_terminate") as terminate:
            with self.assertRaisesRegex(pc.ProcessControlError, "changed identity"):
                pc.apply_close(plan)
            terminate.assert_not_called()


@unittest.skipUnless(os.name == "nt", "CommandLineToArgvW requires Windows")
class WindowsArgvTests(unittest.TestCase):
    def test_quoted_entire_flag_and_split_flag(self):
        whole = f'"{EXE}" "--user-data-dir={PROFILE}"'
        separate = f'"{EXE}" --user-data-dir "{PROFILE}"'
        self.assertEqual(pc._profile_flag(pc._argv(whole)),
                         (False, pc._normal_path(PROFILE)))
        self.assertEqual(pc._profile_flag(pc._argv(separate)),
                         (False, pc._normal_path(PROFILE)))


@unittest.skipUnless(os.name == "nt", "Windows process handles required")
class OwnChildHandleTests(unittest.TestCase):
    def test_pinned_handle_stops_only_spawned_helper(self):
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"],
                                 creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            handle = pc._open(child.pid, terminate=True)
            try:
                created, path = pc._identity(handle)
                self.assertGreater(created, 0)
                self.assertEqual(path, pc._normal_path(sys.executable))
                self.assertTrue(pc._alive(handle))
                pc._terminate(handle, child.pid)
                pc._wait(handle, 5000)
                self.assertFalse(pc._alive(handle))
            finally:
                pc._close(handle)
        finally:
            if child.poll() is None:
                child.terminate()
            child.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
