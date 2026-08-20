#!/usr/bin/env python3
"""Benchmark Neo4j AuraDB (free tier)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
from loaders.bolt_loader import load_graph
from benchmarks.bolt_benchmarker import run_bolt_benchmark

load_dotenv()

if __name__ == "__main__":
    uri = os.environ["NEO4J_URI"]
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ["NEO4J_PASSWORD"]

    print("=" * 60)
    print("BENCHMARK: Neo4j AuraDB")
    print("=" * 60)

    loading = load_graph(uri, user, password, "Neo4j")
    run_bolt_benchmark(uri, user, password, "Neo4j", loading)
