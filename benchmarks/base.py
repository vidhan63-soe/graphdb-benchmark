"""Shared timing utilities and result types for all benchmark scripts."""
import json
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

import numpy as np

WARMUP_ITERS = 10
BENCH_ITERS = 100
MIXED_DURATION_S = 60


@dataclass
class QueryResult:
    name: str
    platform: str
    latencies_ms: List[float] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def p50(self):
        return round(float(np.percentile(self.latencies_ms, 50)), 3) if self.latencies_ms else None

    @property
    def p95(self):
        return round(float(np.percentile(self.latencies_ms, 95)), 3) if self.latencies_ms else None

    @property
    def mean(self):
        return round(float(np.mean(self.latencies_ms)), 3) if self.latencies_ms else None

    def to_dict(self):
        return {
            "p50_ms": self.p50,
            "p95_ms": self.p95,
            "mean_ms": self.mean,
            "iterations": len(self.latencies_ms),
            "error": self.error,
        }


def run_query_bench(
    fn: Callable,
    name: str,
    platform: str,
    warmup: int = WARMUP_ITERS,
    iterations: int = BENCH_ITERS,
) -> QueryResult:
    result = QueryResult(name=name, platform=platform)
    try:
        for _ in range(warmup):
            fn()
        for _ in range(iterations):
            t0 = time.perf_counter()
            fn()
            result.latencies_ms.append((time.perf_counter() - t0) * 1000)
    except Exception as exc:
        result.error = str(exc)
        print(f"  [WARN] {name} on {platform}: {exc}")
    return result


def run_mixed_workload(
    read_fn: Callable,
    write_fn: Callable,
    concurrency: int,
    duration_s: int = MIXED_DURATION_S,
    read_ratio: float = 0.8,
) -> dict:
    import random

    completed = {"n": 0}
    stop = {"flag": False}
    lock = threading.Lock()

    def worker():
        while not stop["flag"]:
            try:
                if random.random() < read_ratio:
                    read_fn()
                else:
                    write_fn()
                with lock:
                    completed["n"] += 1
            except Exception:
                pass

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(concurrency)]
    for t in threads:
        t.start()
    time.sleep(duration_s)
    stop["flag"] = True
    for t in threads:
        t.join(timeout=5)

    return {
        "concurrency": concurrency,
        "duration_s": duration_s,
        "total_queries": completed["n"],
        "qps": round(completed["n"] / duration_s, 2),
    }


def save_results(platform: str, results: dict):
    os.makedirs("results", exist_ok=True)
    fname = platform.lower().replace(" ", "_")
    path = f"results/{fname}.json"
    with open(path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"[{platform}] Results saved → {path}")
