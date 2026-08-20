#!/usr/bin/env python3
"""
Parse the SNAP email-Enron dataset and emit:
  data/nodes.csv       — node_id column
  data/edges.csv       — src, dst columns  (used by most loaders)
  data/edges_raw.csv   — src, dst without header (used by Kuzu COPY FROM)
  data/start_nodes.txt — 100 seed nodes (out-degree 5–20) for traversal benchmarks
"""
import os
import csv
import gzip
import random
from collections import defaultdict

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_FILE = os.path.join(DATA_DIR, "email-Enron.txt.gz")


def parse_snap(path):
    edges = []
    with gzip.open(path, "rt") as f:
        for line in f:
            if line.startswith("#"):
                continue
            parts = line.strip().split()
            if len(parts) == 2:
                src, dst = int(parts[0]), int(parts[1])
                if src != dst:  # skip self-loops
                    edges.append((src, dst))
    return edges


def main():
    print("Parsing dataset …")
    edges = parse_snap(RAW_FILE)

    nodes: set = set()
    out_degree: dict = defaultdict(int)
    for src, dst in edges:
        nodes.add(src)
        nodes.add(dst)
        out_degree[src] += 1

    print(f"  Nodes : {len(nodes):,}")
    print(f"  Edges : {len(edges):,}")

    # nodes.csv
    with open(os.path.join(DATA_DIR, "nodes.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["node_id"])
        for n in sorted(nodes):
            w.writerow([n])

    # edges.csv  (with header — used by Bolt loaders and FalkorDB)
    with open(os.path.join(DATA_DIR, "edges.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["src", "dst"])
        for src, dst in edges:
            w.writerow([src, dst])

    # edges_raw.csv  (no header — used by Kuzu COPY FROM)
    with open(os.path.join(DATA_DIR, "edges_raw.csv"), "w", newline="") as f:
        w = csv.writer(f)
        for src, dst in edges:
            w.writerow([src, dst])

    # start_nodes.txt  — 100 nodes with out-degree 5–20
    candidates = [n for n, d in out_degree.items() if 5 <= d <= 20]
    random.seed(42)
    start_nodes = random.sample(candidates, min(100, len(candidates)))
    with open(os.path.join(DATA_DIR, "start_nodes.txt"), "w") as f:
        for n in start_nodes:
            f.write(f"{n}\n")

    print(f"  Traversal seed nodes : {len(start_nodes)} (out-degree 5–20)")
    print("Done. Written: nodes.csv, edges.csv, edges_raw.csv, start_nodes.txt")


if __name__ == "__main__":
    main()
