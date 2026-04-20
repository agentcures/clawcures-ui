from __future__ import annotations

import argparse
import json
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from clawcures_ui.app import StudioApp, create_server
from clawcures_ui.config import StudioConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark clawcures-ui store methods and HTTP endpoints."
    )
    parser.add_argument("--jobs", type=int, default=200, help="Number of seed jobs.")
    parser.add_argument(
        "--events-per-job",
        type=int,
        default=4,
        help="Number of seed events per completed job.",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=50,
        help="Number of timed iterations per benchmark.",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=5,
        help="Warmup iterations before timing.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=80,
        help="Limit parameter used for jobs and stream payload benchmarks.",
    )
    return parser.parse_args()


def seed_store(app: StudioApp, *, jobs: int, events_per_job: int) -> None:
    for index in range(jobs):
        job = app.store.create_job(
            kind="campaign_run" if index % 2 == 0 else "plan_execute",
            request={"objective": f"Benchmark objective {index}"},
        )
        job_id = str(job["job_id"])
        app.store.set_running(job_id)

        result = {
            "objective": f"Benchmark objective {index}",
            "promising_cures": [
                {
                    "cure_id": f"drug:{index}",
                    "name": f"Candidate {index}",
                    "target": "KRAS G12D" if index % 3 == 0 else "EGFR",
                    "tool": "refua_affinity" if index % 2 == 0 else "refua_admet_profile",
                    "score": 60.0 + (index % 30),
                    "promising": index % 4 == 0,
                    "assessment": "Synthetic benchmark payload.",
                    "metrics": {"binding_probability": 0.55, "admet_score": 0.61},
                    "admet": {"status": "favorable"},
                }
            ],
        }
        app.store.set_completed(job_id, result)
        for event_index in range(events_per_job):
            app.store.record_event(
                job_id,
                event_type="tool_completed",
                summary=f"Seed event {event_index} for job {index}",
                detail={"call_index": event_index + 1, "total_calls": events_per_job},
            )


def benchmark(label: str, iterations: int, warmup: int, fn: Callable[[], Any]) -> None:
    for _ in range(max(warmup, 0)):
        fn()

    durations_ms: list[float] = []
    for _ in range(max(iterations, 1)):
        start = time.perf_counter()
        fn()
        durations_ms.append((time.perf_counter() - start) * 1000.0)

    mean_ms = sum(durations_ms) / len(durations_ms)
    p95_ms = sorted(durations_ms)[max(int(len(durations_ms) * 0.95) - 1, 0)]
    print(f"{label:<28} mean={mean_ms:8.3f} ms  p95={p95_ms:8.3f} ms")


def fetch_json(url: str) -> dict[str, Any]:
    with urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    args = parse_args()
    with tempfile.TemporaryDirectory() as tmpdir:
        config = StudioConfig(
            host="127.0.0.1",
            port=0,
            data_dir=Path(tmpdir) / "data",
            workspace_root=ROOT.parent,
            max_workers=1,
            autostart_agent=False,
        )
        server, app = create_server(config)
        seed_store(app, jobs=args.jobs, events_per_job=args.events_per_job)

        host, port = server.server_address
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            list_query = {"limit": [str(args.limit)]}
            list_query_running = {"limit": [str(args.limit)], "status": ["completed"]}

            benchmark(
                "store.status_counts",
                args.iterations,
                args.warmup,
                app.store.status_counts,
            )
            benchmark(
                "store.list_jobs",
                args.iterations,
                args.warmup,
                lambda: app.store.list_jobs(limit=args.limit),
            )
            benchmark(
                "store.list_events",
                args.iterations,
                args.warmup,
                lambda: app.store.list_events(limit=120),
            )
            benchmark(
                "app.jobs_stream_payload",
                args.iterations,
                args.warmup,
                lambda: app.jobs_stream_payload(query=list_query),
            )
            benchmark(
                "app.jobs_stream_filtered",
                args.iterations,
                args.warmup,
                lambda: app.jobs_stream_payload(query=list_query_running),
            )
            benchmark(
                "store.promising_drugs",
                args.iterations,
                args.warmup,
                lambda: app.store.list_promising_drugs(limit=300),
            )

            jobs_url = f"http://{host}:{port}/api/jobs?limit={args.limit}"
            filtered_url = (
                f"http://{host}:{port}/api/jobs?limit={args.limit}&status=completed"
            )
            promising_url = f"http://{host}:{port}/api/promising-drugs?limit=300"

            benchmark(
                "http.GET /api/jobs",
                args.iterations,
                args.warmup,
                lambda: fetch_json(jobs_url),
            )
            benchmark(
                "http.GET /api/jobs filtered",
                args.iterations,
                args.warmup,
                lambda: fetch_json(filtered_url),
            )
            benchmark(
                "http.GET /api/promising-drugs",
                args.iterations,
                args.warmup,
                lambda: fetch_json(promising_url),
            )
        finally:
            server.shutdown()
            server.server_close()
            app.shutdown()
            thread.join(timeout=2.0)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
