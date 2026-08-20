"""
Shared data loader for Bolt-protocol databases (CognoDB, Neo4j AuraDB, Memgraph).
All three speak Bolt and accept the neo4j Python driver — only the URI and auth differ.
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from neo4j import GraphDatabase
from tqdm import tqdm
from loaders.common import load_nodes_csv, load_edges_csv

BATCH_SIZE = 500


def load_graph(uri: str, user: str, password: str, platform: str) -> dict:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    nodes = load_nodes_csv()
    edges = load_edges_csv()

    print(f"[{platform}] Clearing existing data …")
    with driver.session() as s:
        s.run("MATCH (n) DETACH DELETE n")

    print(f"[{platform}] Creating index …")
    with driver.session() as s:
        try:
            s.run("CREATE INDEX email_id IF NOT EXISTS FOR (n:Email) ON (n.id)")
        except Exception:
            # Memgraph uses legacy index syntax
            try:
                s.run("CREATE INDEX ON :Email(id)")
            except Exception:
                pass

    t_start = time.perf_counter()

    print(f"[{platform}] Loading {len(nodes):,} nodes …")
    with driver.session() as s:
        for i in tqdm(range(0, len(nodes), BATCH_SIZE), desc="  nodes"):
            batch = nodes[i : i + BATCH_SIZE]
            s.run("UNWIND $batch AS id CREATE (:Email {id: id})", batch=batch)

    print(f"[{platform}] Loading {len(edges):,} edges …")
    with driver.session() as s:
        for i in tqdm(range(0, len(edges), BATCH_SIZE), desc="  edges"):
            batch = [{"s": src, "d": dst} for src, dst in edges[i : i + BATCH_SIZE]]
            s.run(
                "UNWIND $batch AS row "
                "MATCH (a:Email {id: row.s}), (b:Email {id: row.d}) "
                "CREATE (a)-[:SENT]->(b)",
                batch=batch,
            )

    elapsed = time.perf_counter() - t_start
    driver.close()

    result = {
        "platform": platform,
        "nodes_loaded": len(nodes),
        "edges_loaded": len(edges),
        "load_time_s": round(elapsed, 2),
        "nodes_per_sec": round(len(nodes) / elapsed, 1),
        "edges_per_sec": round(len(edges) / elapsed, 1),
    }
    print(
        f"[{platform}] Done: {len(nodes):,} nodes + {len(edges):,} edges in {elapsed:.1f}s "
        f"({result['edges_per_sec']:.0f} edges/s)"
    )
    return result
