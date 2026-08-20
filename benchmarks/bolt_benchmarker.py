"""
Shared benchmark logic for Bolt-protocol databases (CognoDB, Neo4j AuraDB, Memgraph).
All three accept the neo4j driver and the same Cypher queries.
"""
import random
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from neo4j import GraphDatabase
from benchmarks.base import (
    BENCH_ITERS,
    WARMUP_ITERS,
    run_mixed_workload,
    run_query_bench,
    save_results,
)
from loaders.common import load_start_nodes


def _session_run(driver, query, params=None):
    with driver.session() as s:
        record = s.run(query, **(params or {})).single()
        return record


def _get_footprint(driver) -> dict:
    """Attempt to read storage metrics; return 'not_observable' if unavailable."""
    try:
        with driver.session() as s:
            # Neo4j / CognoDB — dbms.queryJmx or apoc.monitor.store
            r = s.run(
                "CALL apoc.monitor.store() YIELD logSize, stringStoreSize, arrayStoreSize, "
                "relStoreSize, propStoreSize, totalStoreSize"
            ).single()
            if r:
                return {"total_store_size_bytes": r["totalStoreSize"], "source": "apoc.monitor.store"}
    except Exception:
        pass
    try:
        with driver.session() as s:
            # Memgraph
            rows = list(s.run("SHOW STORAGE INFO"))
            info = {row["storage info"]: row["value"] for row in rows}
            return {"memgraph_storage_info": info, "source": "SHOW STORAGE INFO"}
    except Exception:
        pass
    return {"stored_size": "not_observable", "note": "Free tier does not expose storage metrics"}


def run_bolt_benchmark(uri: str, user: str, password: str, platform: str, loading_result: dict) -> dict:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    start_nodes = load_start_nodes()
    results = {"platform": platform, "loading": loading_result}

    print(f"\n[{platform}] Running traversal benchmarks …")

    traversal_queries = {
        "traversal_1hop": "MATCH (n:Email {{id: $id}})-[:SENT]->(m) RETURN count(m)",
        "traversal_2hop": "MATCH (n:Email {{id: $id}})-[:SENT*2]->(m) RETURN count(DISTINCT m)",
        "traversal_3hop": "MATCH (n:Email {{id: $id}})-[:SENT*3]->(m) RETURN count(DISTINCT m)",
    }

    for bench_name, query_template in traversal_queries.items():
        query = query_template.replace("{{", "{").replace("}}", "}")
        sample = random.choices(start_nodes, k=WARMUP_ITERS + BENCH_ITERS)
        it = iter(sample)

        def make_fn(q, iterator):
            def fn():
                nid = next(iterator)
                _session_run(driver, q, {"id": nid})
            return fn

        print(f"  {bench_name} …")
        bench = run_query_bench(fn=make_fn(query, it), name=bench_name, platform=platform)
        results[bench_name] = bench.to_dict()

    print(f"[{platform}] Running lookup benchmarks …")

    sample = random.choices(start_nodes, k=WARMUP_ITERS + BENCH_ITERS)
    it = iter(sample)
    bench = run_query_bench(
        fn=lambda: _session_run(driver, "MATCH (n:Email) WHERE n.id = $id RETURN n.id", {"id": next(it)}),
        name="lookup_point",
        platform=platform,
    )
    results["lookup_point"] = bench.to_dict()

    sample = random.choices(start_nodes, k=WARMUP_ITERS + BENCH_ITERS)
    it = iter(sample)
    bench = run_query_bench(
        fn=lambda: _session_run(driver, "MATCH (n:Email {id: $id}) RETURN n.id", {"id": next(it)}),
        name="lookup_indexed",
        platform=platform,
    )
    results["lookup_indexed"] = bench.to_dict()

    print(f"[{platform}] Running aggregation benchmarks …")

    bench = run_query_bench(
        fn=lambda: _session_run(driver, "MATCH ()-[:SENT]->() RETURN count(*)"),
        name="aggregation_count",
        platform=platform,
    )
    results["aggregation_count"] = bench.to_dict()

    bench = run_query_bench(
        fn=lambda: _session_run(
            driver,
            "MATCH (n:Email)-[:SENT]->() "
            "WITH n.id AS sender, count(*) AS out_deg "
            "RETURN sender, out_deg ORDER BY out_deg DESC LIMIT 10",
        ),
        name="aggregation_groupby",
        platform=platform,
    )
    results["aggregation_groupby"] = bench.to_dict()

    print(f"[{platform}] Running mixed workload benchmarks …")

    def read_fn():
        nid = random.choice(start_nodes)
        _session_run(driver, "MATCH (n:Email {id: $id})-[:SENT]->(m) RETURN count(m)", {"id": nid})

    def write_fn():
        nid = random.choice(start_nodes)
        ts = int(time.time() * 1000)
        _session_run(driver, "MATCH (n:Email {id: $id}) SET n.ts = $ts RETURN n.id", {"id": nid, "ts": ts})

    for concurrency in [10, 40]:
        print(f"  mixed workload @ {concurrency} clients (60 s) …")
        results[f"mixed_workload_{concurrency}"] = run_mixed_workload(
            read_fn, write_fn, concurrency=concurrency
        )

    results["footprint"] = _get_footprint(driver)
    driver.close()

    save_results(platform, results)
    return results
