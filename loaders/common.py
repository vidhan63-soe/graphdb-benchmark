"""Shared data-reading helpers used by all loaders."""
import csv
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def load_nodes_csv():
    """Return sorted list of node IDs (int)."""
    path = os.path.join(DATA_DIR, "nodes.csv")
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return [int(row["node_id"]) for row in reader]


def load_edges_csv():
    """Return list of (src, dst) int tuples."""
    path = os.path.join(DATA_DIR, "edges.csv")
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return [(int(row["src"]), int(row["dst"])) for row in reader]


def load_start_nodes():
    """Return list of seed node IDs for traversal benchmarks."""
    path = os.path.join(DATA_DIR, "start_nodes.txt")
    with open(path) as f:
        return [int(line.strip()) for line in f if line.strip()]
