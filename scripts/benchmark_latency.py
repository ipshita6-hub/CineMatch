"""Measure real end-to-end API latency and write it to artifacts/metrics/latency.json.

The PRD sets a target of < 200 ms per single-user recommendation request. This
script measures what the running API actually does on this machine; nothing
here assumes or asserts the target has been met.

Usage:  python scripts/benchmark_latency.py [base_url] [requests]
"""

from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path

import httpx
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml import config as C  # noqa: E402


def percentiles(samples: list[float]) -> dict:
    a = np.asarray(samples, dtype=float)
    return {
        "count": int(a.size),
        "p50_ms": round(float(np.percentile(a, 50)), 2),
        "p95_ms": round(float(np.percentile(a, 95)), 2),
        "p99_ms": round(float(np.percentile(a, 99)), 2),
        "mean_ms": round(float(a.mean()), 2),
        "min_ms": round(float(a.min()), 2),
        "max_ms": round(float(a.max()), 2),
    }


def main() -> None:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    rng = random.Random(C.SEED)

    import pandas as pd
    user_ids = pd.read_csv(C.USER_MAPPING_CSV)["userId"].to_numpy()

    scenarios: dict[str, dict] = {}
    with httpx.Client(timeout=30.0) as client:
        if client.get(f"{base}/health").status_code != 200:
            print(f"API at {base} is not healthy; start the backend first.")
            return

        def run(name: str, call) -> None:
            call()                                   # warm-up, not measured
            samples = []
            for _ in range(n):
                t0 = time.perf_counter()
                r = call()
                samples.append((time.perf_counter() - t0) * 1000)
                r.raise_for_status()
            scenarios[name] = percentiles(samples)
            print(f"{name:46s} p50={scenarios[name]['p50_ms']:7.2f}ms "
                  f"p95={scenarios[name]['p95_ms']:7.2f}ms", flush=True)

        # Distinct users each call, so the response cache cannot flatter the result
        run("GET /recommendations/{user_id} (neumf, k=10)",
            lambda: client.get(f"{base}/recommendations/{rng.choice(user_ids)}",
                               params={"limit": 10, "model": "neumf"}))
        run("GET /recommendations/{user_id} (neumf, k=50)",
            lambda: client.get(f"{base}/recommendations/{rng.choice(user_ids)}",
                               params={"limit": 50, "model": "neumf"}))
        run("GET /recommendations/{user_id} (hybrid, k=10)",
            lambda: client.get(f"{base}/recommendations/{rng.choice(user_ids)}",
                               params={"limit": 10, "model": "hybrid"}))
        run("GET /recommendations/{user_id} (popularity fallback)",
            lambda: client.get(f"{base}/recommendations/{rng.choice(user_ids)}",
                               params={"limit": 10, "model": "popularity"}))
        run("POST /predict",
            lambda: client.post(f"{base}/predict",
                                json={"user_id": int(rng.choice(user_ids)), "movie_id": 2571}))
        run("GET /movies (search)",
            lambda: client.get(f"{base}/movies", params={"search": "star", "page_size": 24}))
        run("GET /metrics", lambda: client.get(f"{base}/metrics"))
        run("GET /health", lambda: client.get(f"{base}/health"))

    primary = scenarios["GET /recommendations/{user_id} (neumf, k=10)"]
    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "base_url": base,
        "requests_per_scenario": n,
        "target_ms": 200,
        "measured_on": "local development machine (Apple silicon, CPU inference)",
        "note": ("Measured against a locally running API with a warm TMDB metadata cache. "
                 "A cold TMDB lookup adds network time; run scripts/prewarm_tmdb.py first. "
                 "These figures describe this machine, not a production deployment."),
        "scenarios": scenarios,
        "primary_scenario": "GET /recommendations/{user_id} (neumf, k=10)",
        "primary_p50_ms": primary["p50_ms"],
        "primary_p95_ms": primary["p95_ms"],
        "meets_target_p95": bool(primary["p95_ms"] < 200),
    }
    C.LATENCY_JSON.write_text(json.dumps(out, indent=2))
    print(f"\nPrimary scenario p50={primary['p50_ms']}ms p95={primary['p95_ms']}ms "
          f"(target 200ms) -> {'met' if out['meets_target_p95'] else 'NOT met'}")
    print(f"Written to {C.LATENCY_JSON}")


if __name__ == "__main__":
    main()
