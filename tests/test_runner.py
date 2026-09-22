from __future__ import annotations

import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from clawcures_ui.runner import BackgroundRunner  # noqa: E402
from clawcures_ui.storage import JobStore  # noqa: E402


class BackgroundRunnerCancelTest(unittest.TestCase):
    def test_cancel_succeeds_when_queued_future_already_started(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        store = JobStore(Path(tmp.name) / "jobs.sqlite")
        runner = BackgroundRunner(store, max_workers=1)
        started = threading.Event()
        release = threading.Event()

        def hold(**_kwargs: object) -> dict[str, bool]:
            started.set()
            self.assertTrue(release.wait(3))
            return {"ok": True}

        def finish(**_kwargs: object) -> dict[str, bool]:
            return {"ok": True}

        try:
            runner.submit(kind="hold", request={}, fn=hold)
            self.assertTrue(started.wait(3))
            queued = runner.submit(kind="queued", request={}, fn=finish)
            future = runner._futures[queued["job_id"]]
            future.cancel = lambda: False  # type: ignore[method-assign]
            result = runner.cancel(queued["job_id"])
            self.assertTrue(result["cancelled"])
            release.set()

            status = "queued"
            deadline = time.time() + 3
            while time.time() < deadline:
                latest = store.get_job(queued["job_id"])
                status = str(latest["status"]) if latest else status
                if status in {"cancelled", "completed", "failed"}:
                    break
                time.sleep(0.02)
            self.assertEqual(status, "cancelled")
        finally:
            release.set()
            runner.shutdown()
            store.shutdown()
            tmp.cleanup()
