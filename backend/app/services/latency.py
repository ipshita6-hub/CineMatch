"""Rolling, measured request-latency statistics (no estimates)."""

from __future__ import annotations

import threading
from collections import defaultdict, deque

import numpy as np


class LatencyTracker:
    def __init__(self, window: int = 1000):
        self.window = window
        self._samples: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=window))
        self._lock = threading.Lock()

    def record(self, route: str, ms: float) -> None:
        with self._lock:
            self._samples[route].append(ms)

    def snapshot(self) -> dict:
        with self._lock:
            data = {k: list(v) for k, v in self._samples.items() if v}
        out = {}
        for route, vals in data.items():
            arr = np.asarray(vals, dtype=float)
            out[route] = {
                "count": int(arr.size),
                "p50_ms": round(float(np.percentile(arr, 50)), 2),
                "p95_ms": round(float(np.percentile(arr, 95)), 2),
                "p99_ms": round(float(np.percentile(arr, 99)), 2),
                "mean_ms": round(float(arr.mean()), 2),
                "max_ms": round(float(arr.max()), 2),
            }
        return out


latency_tracker = LatencyTracker()
