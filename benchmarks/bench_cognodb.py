#!/usr/bin/env python3
"""Benchmark CognoDB Cloud (free c0 tier)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
from loaders.bolt_loader import load_graph
from benchmarks.bolt_benchmarker import run_bolt_benchmark

load_dotenv()

if __name__ == "__main__":
    uri = os.environ["COGNODB_URI"]
    user = os.environ.get("COGNODB_USER", "cognodb")
    password = os.environ["COGNODB_PASSWORD"]

    print("=" * 60)
    print("BENCHMARK: CognoDB Cloud")
    print("=" * 60)

    loading = load_graph(uri, user, password, "CognoDB")
    run_bolt_benchmark(uri, user, password, "CognoDB", loading)
