#!/usr/bin/env python3
"""
Load email-Enron dataset into Kuzu (embedded, columnar graph DB).
Uses COPY FROM CSV for nodes (fast), Python batches for edges.
"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
from tqdm import tqdm
import kuzu
from loaders.common import load_edges_csv

load_dotenv()

BATCH_SIZE = 1000


def load_graph_kuzu(db_path: str) -> dict:
    import shutil

    if os.path.exists(db_path):
        shutil.rmtree(db_path)

    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)

    nodes_csv = os.path.abspath("data/nodes.csv")
    edges_raw_csv = os.path.abspath("data/edges_raw.csv")

    print("[Kuzu] Creating schema …")
    conn.execute("CREATE NODE TABLE Email(id INT64, PRIMARY KEY(id))")
    conn.execute("CREATE REL TABLE SENT(FROM Email TO Email)")

    t_start = time.perf_counter()

    print("[Kuzu] Loading nodes via COPY FROM CSV …")
    conn.execute(f"COPY Email FROM '{nodes_csv}' (HEADER=true)")

    node_result = conn.execute("MATCH (n:Email) RETURN count(n)")
    node_count = node_result.get_next()[0]
    print(f"[Kuzu]   {node_count:,} nodes loaded")

    print("[Kuzu] Loading edges via COPY FROM CSV …")
    # edges_raw.csv has no header; Kuzu reads col0=from_pk, col1=to_pk positionally
    conn.execute(f"COPY SENT FROM '{edges_raw_csv}' (HEADER=false)")

    edge_result = conn.execute("MATCH ()-[:SENT]->() RETURN count(*)")
    edge_count = edge_result.get_next()[0]
    print(f"[Kuzu]   {edge_count:,} edges loaded")

    elapsed = time.perf_counter() - t_start

    result = {
        "platform": "Kuzu",
        "nodes_loaded": node_count,
        "edges_loaded": edge_count,
        "load_time_s": round(elapsed, 2),
        "nodes_per_sec": round(node_count / elapsed, 1),
        "edges_per_sec": round(edge_count / elapsed, 1),
    }
    print(
        f"[Kuzu] Done: {node_count:,} nodes + {edge_count:,} edges "
        f"in {elapsed:.1f}s ({result['edges_per_sec']:.0f} edges/s)"
    )
    return result


if __name__ == "__main__":
    db_path = os.environ.get("KUZU_DB_PATH", "./kuzu_benchmark_db")
    result = load_graph_kuzu(db_path)
    print(json.dumps(result, indent=2))
