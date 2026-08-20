#!/usr/bin/env python3
"""Load email-Enron dataset into FalkorDB (Docker, resource-capped)."""
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
from tqdm import tqdm
from falkordb import FalkorDB
from loaders.common import load_nodes_csv, load_edges_csv

load_dotenv()

GRAPH_NAME = "email_benchmark"
BATCH_SIZE = 500


def load_graph_falkordb(host: str, port: int) -> dict:
    client = FalkorDB(host=host, port=port)
    g = client.select_graph(GRAPH_NAME)

    nodes = load_nodes_csv()
    edges = load_edges_csv()

    print("[FalkorDB] Clearing existing graph …")
    try:
        g.delete()
    except Exception:
        pass
    g = client.select_graph(GRAPH_NAME)

    print("[FalkorDB] Creating index …")
    g.create_node_range_index("Email", "id")

    t_start = time.perf_counter()

    print(f"[FalkorDB] Loading {len(nodes):,} nodes …")
    for i in tqdm(range(0, len(nodes), BATCH_SIZE), desc="  nodes"):
        batch = nodes[i : i + BATCH_SIZE]
        g.query("UNWIND $batch AS id CREATE (:Email {id: id})", {"batch": batch})

    print(f"[FalkorDB] Loading {len(edges):,} edges …")
    for i in tqdm(range(0, len(edges), BATCH_SIZE), desc="  edges"):
        batch = [[s, d] for s, d in edges[i : i + BATCH_SIZE]]
        g.query(
            "UNWIND $batch AS row "
            "MATCH (a:Email {id: row[0]}), (b:Email {id: row[1]}) "
            "CREATE (a)-[:SENT]->(b)",
            {"batch": batch},
        )

    elapsed = time.perf_counter() - t_start

    result = {
        "platform": "FalkorDB",
        "nodes_loaded": len(nodes),
        "edges_loaded": len(edges),
        "load_time_s": round(elapsed, 2),
        "nodes_per_sec": round(len(nodes) / elapsed, 1),
        "edges_per_sec": round(len(edges) / elapsed, 1),
    }
    print(
        f"[FalkorDB] Done: {len(nodes):,} nodes + {len(edges):,} edges "
        f"in {elapsed:.1f}s ({result['edges_per_sec']:.0f} edges/s)"
    )
    return result


if __name__ == "__main__":
    host = os.environ.get("FALKORDB_HOST", "localhost")
    port = int(os.environ.get("FALKORDB_PORT", "6379"))

    result = load_graph_falkordb(host, port)
    print(json.dumps(result, indent=2))
