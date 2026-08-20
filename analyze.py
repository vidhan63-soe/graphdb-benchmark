#!/usr/bin/env python3
"""
Reads results/*.json and produces:
  - A console summary table (all metrics, all platforms)
  - charts/  with PNG bar charts for each metric category
"""
import glob
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from tabulate import tabulate

RESULTS_DIR = "results"
CHARTS_DIR = "charts"

PLATFORMS_ORDER = ["CognoDB", "Neo4j", "FalkorDB", "Memgraph", "Kuzu"]
COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]


def load_results() -> dict:
    data = {}
    for path in glob.glob(os.path.join(RESULTS_DIR, "*.json")):
        with open(path) as f:
            r = json.load(f)
        data[r["platform"]] = r
    return data


def fmt(val, unit=""):
    if val is None:
        return "—"
    if isinstance(val, float):
        return f"{val:.1f}{unit}"
    return str(val)


def print_summary(data: dict):
    platforms = [p for p in PLATFORMS_ORDER if p in data]
    headers = ["Metric"] + platforms

    rows = []

    # Loading
    rows.append(["**DATA LOADING**"] + [""] * len(platforms))
    rows.append(
        ["Nodes/sec"] + [fmt(data[p]["loading"].get("nodes_per_sec")) for p in platforms]
    )
    rows.append(
        ["Edges/sec"] + [fmt(data[p]["loading"].get("edges_per_sec")) for p in platforms]
    )
    rows.append(
        ["Load time (s)"] + [fmt(data[p]["loading"].get("load_time_s"), "s") for p in platforms]
    )

    # Traversals
    rows.append(["**TRAVERSALS (ms)**"] + [""] * len(platforms))
    for hop in [1, 2, 3]:
        key = f"traversal_{hop}hop"
        rows.append(
            [f"{hop}-hop p50"]
            + [fmt(data[p].get(key, {}).get("p50_ms")) for p in platforms]
        )
        rows.append(
            [f"{hop}-hop p95"]
            + [fmt(data[p].get(key, {}).get("p95_ms")) for p in platforms]
        )

    # Lookups
    rows.append(["**LOOKUPS (ms)**"] + [""] * len(platforms))
    for label, key in [("Point p50", "lookup_point"), ("Point p95", "lookup_point"),
                       ("Indexed p50", "lookup_indexed"), ("Indexed p95", "lookup_indexed")]:
        stat = "p50_ms" if "p50" in label else "p95_ms"
        rows.append([label] + [fmt(data[p].get(key, {}).get(stat)) for p in platforms])

    # Aggregations
    rows.append(["**AGGREGATIONS (ms)**"] + [""] * len(platforms))
    for label, key in [("Count p50", "aggregation_count"), ("Count p95", "aggregation_count"),
                       ("Group-by p50", "aggregation_groupby"), ("Group-by p95", "aggregation_groupby")]:
        stat = "p50_ms" if "p50" in label else "p95_ms"
        rows.append([label] + [fmt(data[p].get(key, {}).get(stat)) for p in platforms])

    # Mixed workload
    rows.append(["**MIXED WORKLOAD (QPS)**"] + [""] * len(platforms))
    for c in [10, 40]:
        key = f"mixed_workload_{c}"
        rows.append(
            [f"{c} clients"]
            + [fmt(data[p].get(key, {}).get("qps")) for p in platforms]
        )

    print("\n" + "=" * 70)
    print("BENCHMARK RESULTS SUMMARY")
    print("=" * 70)
    print(tabulate(rows, headers=headers, tablefmt="github"))
    print()


def bar_chart(title: str, metric_keys: list, labels: list, data: dict, filename: str):
    platforms = [p for p in PLATFORMS_ORDER if p in data]
    x = np.arange(len(labels))
    width = 0.8 / len(platforms)

    fig, ax = plt.subplots(figsize=(10, 5))
    for i, (platform, color) in enumerate(zip(platforms, COLORS)):
        vals = []
        for key, stat in metric_keys:
            v = data[platform].get(key, {}).get(stat)
            vals.append(v if v is not None else 0)
        offset = (i - len(platforms) / 2 + 0.5) * width
        ax.bar(x + offset, vals, width, label=platform, color=color)

    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylabel("ms" if "ms" in filename else "")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    os.makedirs(CHARTS_DIR, exist_ok=True)
    path = os.path.join(CHARTS_DIR, filename)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Chart saved → {path}")


def generate_charts(data: dict):
    # Traversal latency p50
    bar_chart(
        "Traversal Latency — p50 (ms)",
        [("traversal_1hop", "p50_ms"), ("traversal_2hop", "p50_ms"), ("traversal_3hop", "p50_ms")],
        ["1-hop", "2-hop", "3-hop"],
        data,
        "traversal_p50.png",
    )
    bar_chart(
        "Traversal Latency — p95 (ms)",
        [("traversal_1hop", "p95_ms"), ("traversal_2hop", "p95_ms"), ("traversal_3hop", "p95_ms")],
        ["1-hop", "2-hop", "3-hop"],
        data,
        "traversal_p95.png",
    )

    # Lookup latency
    bar_chart(
        "Lookup Latency — p50 (ms)",
        [("lookup_point", "p50_ms"), ("lookup_indexed", "p50_ms")],
        ["Point lookup", "Indexed lookup"],
        data,
        "lookup_p50.png",
    )

    # Aggregation
    bar_chart(
        "Aggregation Latency — p50 (ms)",
        [("aggregation_count", "p50_ms"), ("aggregation_groupby", "p50_ms")],
        ["Count(*)", "Group-by top-10"],
        data,
        "aggregation_p50.png",
    )

    # Mixed workload QPS
    platforms = [p for p in PLATFORMS_ORDER if p in data]
    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(2)
    width = 0.8 / len(platforms)
    for i, (p, color) in enumerate(zip(platforms, COLORS)):
        vals = [
            data[p].get("mixed_workload_10", {}).get("qps", 0) or 0,
            data[p].get("mixed_workload_40", {}).get("qps", 0) or 0,
        ]
        offset = (i - len(platforms) / 2 + 0.5) * width
        ax.bar(x + offset, vals, width, label=p, color=color)
    ax.set_title("Mixed Workload Throughput (QPS)")
    ax.set_xticks(x)
    ax.set_xticklabels(["10 clients", "40 clients"])
    ax.set_ylabel("Queries / second")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    path = os.path.join(CHARTS_DIR, "mixed_workload_qps.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Chart saved → {path}")

    # Loading throughput
    platforms_present = [p for p in PLATFORMS_ORDER if p in data]
    edges_per_sec = [data[p]["loading"].get("edges_per_sec", 0) or 0 for p in platforms_present]
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(platforms_present, edges_per_sec, color=COLORS[: len(platforms_present)])
    ax.set_title("Data Loading Throughput (edges/second)")
    ax.set_ylabel("Edges / second")
    for bar, val in zip(bars, edges_per_sec):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 10, f"{val:.0f}", ha="center")
    fig.tight_layout()
    path = os.path.join(CHARTS_DIR, "loading_throughput.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Chart saved → {path}")


def main():
    data = load_results()
    if not data:
        print("No result files found in results/. Run the benchmarks first.")
        return

    print(f"Loaded results for: {', '.join(data.keys())}")
    print_summary(data)
    generate_charts(data)


if __name__ == "__main__":
    main()
