#!/usr/bin/env python3
"""Benchmark Memgraph (Docker, capped to 0.5 vCPU / 256 MB)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
from loaders.bolt_loader import load_graph
from benchmarks.bolt_benchmarker import run_bolt_benchmark

load_dotenv()

if __name__ == "__main__":
    uri = os.environ.get("MEMGRAPH_URI", "bolt://localhost:7688")
    user = os.environ.get("MEMGRAPH_USER", "")
    password = os.environ.get("MEMGRAPH_PASSWORD", "")

    print("=" * 60)
    print("BENCHMARK: Memgraph")
    print("=" * 60)

    loading = load_graph(uri, user, password, "Memgraph")
    run_bolt_benchmark(uri, user, password, "Memgraph", loading)
