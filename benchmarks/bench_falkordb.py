#!/usr/bin/env python3
"""Benchmark FalkorDB (Docker, capped to 0.5 vCPU / 256 MB)."""
import os
import sys
import random
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
from falkordb import FalkorDB
from benchmarks.base import (
    BENCH_ITERS,
    WARMUP_ITERS,
    run_mixed_workload,
    run_query_bench,
    save_results,
)
from loaders.common import load_start_nodes
from loaders.load_falkordb import load_graph_falkordb

load_dotenv()

GRAPH_NAME = "email_benchmark"


def _query(graph, q, params=None):
    result = graph.query(q, params or {})
    return result.result_set


def run_falkordb_benchmark(host: str, port: int, loading_result: dict) -> dict:
    client = FalkorDB(host=host, port=port)
    g = client.select_graph(GRAPH_NAME)
    start_nodes = load_start_nodes()
    results = {"platform": "FalkorDB", "loading": loading_result}

    print("\n[FalkorDB] Running traversal benchmarks …")

    traversal_queries = {
        "traversal_1hop": "MATCH (n:Email {id: $id})-[:SENT]->(m) RETURN count(m)",
        "traversal_2hop": "MATCH (n:Email {id: $id})-[:SENT*2]->(m) RETURN count(DISTINCT m)",
        "traversal_3hop": "MATCH (n:Email {id: $id})-[:SENT*3]->(m) RETURN count(DISTINCT m)",
    }

    for bench_name, query in traversal_queries.items():
        sample = random.choices(start_nodes, k=WARMUP_ITERS + BENCH_ITERS)
        it = iter(sample)

        def make_fn(q, iterator, graph=g):
            def fn():
                nid = next(iterator)
                _query(graph, q, {"id": nid})
            return fn

        print(f"  {bench_name} …")
        bench = run_query_bench(fn=make_fn(query, it), name=bench_name, platform="FalkorDB")
        results[bench_name] = bench.to_dict()

    print("[FalkorDB] Running lookup benchmarks …")

    sample = random.choices(start_nodes, k=WARMUP_ITERS + BENCH_ITERS)
    it = iter(sample)
    bench = run_query_bench(
        fn=lambda: _query(g, "MATCH (n:Email) WHERE n.id = $id RETURN n.id", {"id": next(it)}),
        name="lookup_point",
        platform="FalkorDB",
    )
    results["lookup_point"] = bench.to_dict()

    sample = random.choices(start_nodes, k=WARMUP_ITERS + BENCH_ITERS)
    it = iter(sample)
    bench = run_query_bench(
        fn=lambda: _query(g, "MATCH (n:Email {id: $id}) RETURN n.id", {"id": next(it)}),
        name="lookup_indexed",
        platform="FalkorDB",
    )
    results["lookup_indexed"] = bench.to_dict()

    print("[FalkorDB] Running aggregation benchmarks …")

    bench = run_query_bench(
        fn=lambda: _query(g, "MATCH ()-[:SENT]->() RETURN count(*)"),
        name="aggregation_count",
        platform="FalkorDB",
    )
    results["aggregation_count"] = bench.to_dict()

    bench = run_query_bench(
        fn=lambda: _query(
            g,
            "MATCH (n:Email)-[:SENT]->() "
            "WITH n.id AS sender, count(*) AS out_deg "
            "RETURN sender, out_deg ORDER BY out_deg DESC LIMIT 10",
        ),
        name="aggregation_groupby",
        platform="FalkorDB",
    )
    results["aggregation_groupby"] = bench.to_dict()

    print("[FalkorDB] Running mixed workload benchmarks …")

    # FalkorDB uses Redis single-threaded model; writes are serialised — document as caveat.
    def read_fn():
        nid = random.choice(start_nodes)
        _query(g, "MATCH (n:Email {id: $id})-[:SENT]->(m) RETURN count(m)", {"id": nid})

    def write_fn():
        nid = random.choice(start_nodes)
        ts = int(time.time() * 1000)
        _query(g, "MATCH (n:Email {id: $id}) SET n.ts = $ts RETURN n.id", {"id": nid, "ts": ts})

    for concurrency in [10, 40]:
        print(f"  mixed workload @ {concurrency} clients (60 s) …")
        results[f"mixed_workload_{concurrency}"] = run_mixed_workload(
            read_fn,
            write_fn,
            concurrency=concurrency,
        )

    # FalkorDB footprint: use GRAPH.INFO via raw query
    try:
        info = g.query("CALL db.info()").result_set
        results["footprint"] = {"db_info": str(info), "source": "CALL db.info()"}
    except Exception:
        results["footprint"] = {
            "stored_size": "not_observable",
            "note": "CALL db.info() not available on this FalkorDB version",
        }

    save_results("FalkorDB", results)
    return results


if __name__ == "__main__":
    host = os.environ.get("FALKORDB_HOST", "localhost")
    port = int(os.environ.get("FALKORDB_PORT", "6379"))

    print("=" * 60)
    print("BENCHMARK: FalkorDB")
    print("=" * 60)

    loading = load_graph_falkordb(host, port)
    run_falkordb_benchmark(host, port, loading)
