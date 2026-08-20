#!/usr/bin/env python3
"""Benchmark Kuzu (embedded columnar graph DB, resource-equivalent to free tiers)."""
import os
import sys
import random
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
import kuzu
from benchmarks.base import (
    BENCH_ITERS,
    WARMUP_ITERS,
    run_mixed_workload,
    run_query_bench,
    save_results,
)
from loaders.common import load_start_nodes
from loaders.load_kuzu import load_graph_kuzu

load_dotenv()


def _qval(result):
    """Extract the scalar value from a Kuzu QueryResult."""
    if result.has_next():
        return result.get_next()[0]
    return None


def run_kuzu_benchmark(db_path: str, loading_result: dict) -> dict:
    db = kuzu.Database(db_path, read_only=False)
    conn = kuzu.Connection(db)
    start_nodes = load_start_nodes()
    results = {"platform": "Kuzu", "loading": loading_result}

    print("\n[Kuzu] Running traversal benchmarks …")

    traversal_queries = {
        "traversal_1hop": "MATCH (n:Email)-[:SENT]->(m) WHERE n.id = $id RETURN count(m)",
        "traversal_2hop": "MATCH (n:Email)-[:SENT*2]->(m) WHERE n.id = $id RETURN count(DISTINCT m.id)",
        "traversal_3hop": "MATCH (n:Email)-[:SENT*3]->(m) WHERE n.id = $id RETURN count(DISTINCT m.id)",
    }

    for bench_name, query in traversal_queries.items():
        sample = random.choices(start_nodes, k=WARMUP_ITERS + BENCH_ITERS)
        it = iter(sample)

        def make_fn(q, iterator, connection=conn):
            def fn():
                nid = next(iterator)
                _qval(connection.execute(q, {"id": nid}))
            return fn

        print(f"  {bench_name} …")
        bench = run_query_bench(fn=make_fn(query, it), name=bench_name, platform="Kuzu")
        results[bench_name] = bench.to_dict()

    print("[Kuzu] Running lookup benchmarks …")

    sample = random.choices(start_nodes, k=WARMUP_ITERS + BENCH_ITERS)
    it = iter(sample)
    bench = run_query_bench(
        fn=lambda: _qval(conn.execute("MATCH (n:Email) WHERE n.id = $id RETURN n.id", {"id": next(it)})),
        name="lookup_point",
        platform="Kuzu",
    )
    results["lookup_point"] = bench.to_dict()

    # Kuzu PKs are always indexed — this is the same as the point lookup
    sample = random.choices(start_nodes, k=WARMUP_ITERS + BENCH_ITERS)
    it = iter(sample)
    bench = run_query_bench(
        fn=lambda: _qval(conn.execute("MATCH (n:Email) WHERE n.id = $id RETURN n.id", {"id": next(it)})),
        name="lookup_indexed",
        platform="Kuzu",
    )
    results["lookup_indexed"] = bench.to_dict()
    results["lookup_indexed"]["note"] = "Kuzu PKs are always indexed; same as point lookup"

    print("[Kuzu] Running aggregation benchmarks …")

    bench = run_query_bench(
        fn=lambda: _qval(conn.execute("MATCH ()-[:SENT]->() RETURN count(*)")),
        name="aggregation_count",
        platform="Kuzu",
    )
    results["aggregation_count"] = bench.to_dict()

    bench = run_query_bench(
        fn=lambda: conn.execute(
            "MATCH (n:Email)-[:SENT]->() "
            "WITH n.id AS sender, count(*) AS out_deg "
            "RETURN sender, out_deg ORDER BY out_deg DESC LIMIT 10"
        ).get_as_pl(),
        name="aggregation_groupby",
        platform="Kuzu",
    )
    results["aggregation_groupby"] = bench.to_dict()

    print("[Kuzu] Running mixed workload benchmarks …")

    # Kuzu write transactions are serialised (single-writer MVCC).
    # Concurrent reads are fine; writes contend on a single lock.

    def read_fn():
        nid = random.choice(start_nodes)
        _qval(conn.execute(
            "MATCH (n:Email)-[:SENT]->(m) WHERE n.id = $id RETURN count(m)", {"id": nid}
        ))

    def write_fn():
        nid = random.choice(start_nodes)
        ts = int(time.time() * 1000)
        conn.execute("MATCH (n:Email) WHERE n.id = $id SET n.ts = $ts", {"id": nid, "ts": ts})

    for concurrency in [10, 40]:
        print(f"  mixed workload @ {concurrency} clients (60 s) …")
        mw = run_mixed_workload(read_fn, write_fn, concurrency=concurrency)
        mw["note"] = "Kuzu uses single-writer MVCC; write throughput is serialised"
        results[f"mixed_workload_{concurrency}"] = mw

    # Footprint: directory size on disk
    try:
        total = sum(
            os.path.getsize(os.path.join(dp, f))
            for dp, _, files in os.walk(db_path)
            for f in files
        )
        results["footprint"] = {
            "stored_size_mb": round(total / 1024**2, 2),
            "source": "directory size on disk",
        }
    except Exception as exc:
        results["footprint"] = {"error": str(exc)}

    save_results("Kuzu", results)
    return results


if __name__ == "__main__":
    db_path = os.environ.get("KUZU_DB_PATH", "./kuzu_benchmark_db")

    print("=" * 60)
    print("BENCHMARK: Kuzu")
    print("=" * 60)

    loading = load_graph_kuzu(db_path)
    run_kuzu_benchmark(db_path, loading)
