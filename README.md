# Graph Database Cloud Benchmarking

A reproducible benchmark suite comparing **CognoDB Cloud** against four other managed/self-hosted graph databases on identical hardware resources and the same dataset.

> **Submitted for:** Wexa AI – Take-Home Assignment  
> **Author:** Vidhan  
> **Submission email:** hr@wexa.ai

---

## Table of Contents
1. [Databases Tested](#1-databases-tested)
2. [Dataset](#2-dataset)
3. [Methodology](#3-methodology)
4. [Environment & Instance Specs](#4-environment--instance-specs)
5. [How to Reproduce](#5-how-to-reproduce)
6. [Results](#6-results)
7. [Analysis](#7-analysis)
8. [Caveats & Honest Notes](#8-caveats--honest-notes)

---

## 1. Databases Tested

| # | Platform | Tier / Deployment | Driver | Version |
|---|---|---|---|---|
| 1 | **CognoDB Cloud** | Free (c0) — 0.5 vCPU, 256 MB RAM, 1 GB disk | Neo4j Bolt | Latest free tier |
| 2 | **Neo4j AuraDB** | Free — 200 k nodes / 400 k rels | Neo4j Bolt 5.x | Latest free tier |
| 3 | **FalkorDB** | Docker (capped: 0.5 CPU, 256 MB) | FalkorDB Python 1.x | `falkordb/falkordb:latest` |
| 4 | **Memgraph** | Docker (capped: 0.5 CPU, 256 MB) | Neo4j Bolt via `neo4j` driver | `memgraph/memgraph:2.18.1` |
| 5 | **Kuzu** | Embedded Python (resource-equivalent) | `kuzu` Python SDK 0.6.x | Latest PyPI |

**Why these four?**
- **Neo4j AuraDB** is the market leader and a natural reference point.
- **FalkorDB** uses a fundamentally different internal engine (sparse-matrix / linear algebra), making it an interesting architectural contrast.
- **Memgraph** is a C++ in-memory engine that prioritises low latency over durability — a direct speed challenger.
- **Kuzu** is a modern columnar graph database with Cypher support; it represents the state-of-the-art in analytical graph workloads and is increasingly used in ML pipelines.

---

## 2. Dataset

**SNAP email-Enron**  
Source: https://snap.stanford.edu/data/email-Enron.html  
License: [SNAP General Terms](https://snap.stanford.edu/snap/terms.html)

| Property | Value |
|---|---|
| Node count | 36,692 |
| Edge count | 183,831 |
| Graph type | Directed |
| Node label | `Email` (property: `id INT64`) |
| Relationship type | `SENT` |
| Self-loops | Removed |

The dataset is an email communication network from the Enron corpus. Nodes are email addresses; a directed edge `(a)-[:SENT]->(b)` means address `a` sent at least one email to address `b`.

**Why this dataset?**  
It is within the free-tier capacity of every tested platform (≤ 36 k nodes, ≤ 184 k edges), publicly available, well-cited, and realistic enough to produce meaningful traversal fan-out at all hop depths.

**Traversal seed nodes:** 100 nodes with out-degree 5–20 were pre-selected (seed 42) to avoid skewed results from hub nodes or isolated sinks. The same 100 nodes are used across all platforms.

---

## 3. Methodology

### Fairness rules followed
- **Same resources everywhere:** all platforms capped at 0.5 vCPU and 256 MB RAM. Free cloud tiers are documented with their advertised specs; Docker containers are hard-capped with `deploy.resources.limits`.
- **Same dataset:** identical `nodes.csv` and `edges.csv` loaded into every platform.
- **Same logical queries:** Cypher is used for all platforms that support it (CognoDB, Neo4j, FalkorDB, Memgraph, Kuzu). Where syntax differs, the logical query is identical.
- **Same client machine:** all benchmarks run from the same host.
- **Warm-up:** 10 query iterations are discarded before recording begins.
- **Measurement:** 100 iterations per read workload. p50 and p95 are reported; averages alone are not.
- **Mixed workload:** 60-second window, 80 % reads (random 1-hop traversal) / 20 % writes (set a timestamp property). Run at both 10 and 40 concurrent clients.

### Metrics

| Category | Metric | Reported |
|---|---|---|
| Data loading | Ingest throughput | nodes/sec, edges/sec, total wall-clock time |
| Traversals | 1-hop, 2-hop, 3-hop query latency | p50 + p95 (ms) from 100 seed-node starts |
| Lookups | Point lookup (scan), indexed lookup | p50 + p95 (ms) |
| Aggregations | `count(*)`, top-10 group-by out-degree | p50 + p95 (ms) |
| Mixed workload | Concurrent read/write | QPS at 10 and 40 clients |
| Footprint | Storage / memory | Platform-observable metrics or "not_observable" |

---

## 4. Environment & Instance Specs

| Platform | vCPU | RAM | Disk | Region / Host |
|---|---|---|---|---|
| CognoDB Cloud | 0.5 (burstable) | 256 MB | 1 GB | (your chosen region) |
| Neo4j AuraDB | ~0.5 (burstable free) | 256 MB | ~1 GB | (your chosen region) |
| FalkorDB | 0.5 (Docker limit) | 256 MB | Host disk | localhost |
| Memgraph | 0.5 (Docker limit) | 256 MB (--memory-limit) | Host disk | localhost |
| Kuzu | 0.5 (Docker/process limit) | 256 MB | Host disk | embedded |

Client machine: _fill in your specs here, e.g. "Ubuntu 22.04, 8-core Intel i7, 16 GB RAM, gigabit LAN"_

---

## 5. How to Reproduce

### Prerequisites
- Python ≥ 3.10
- Docker + Docker Compose v2
- Free accounts on: CognoDB Cloud, Neo4j AuraDB

### Steps

```bash
# 1. Clone the repo
git clone <repo-url>
cd graph-db-benchmark

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set credentials
cp .env.example .env
# Edit .env with your CognoDB and Neo4j AuraDB connection details

# 4. Run everything (dataset download → load → benchmark → charts)
./run_all.sh
```

The script will:
1. Download the email-Enron dataset from SNAP (~1.3 MB gzip)
2. Prepare `nodes.csv`, `edges.csv`, `start_nodes.txt`
3. Start FalkorDB + Memgraph via Docker Compose
4. Load data and run all benchmarks on all 5 platforms
5. Print the results table and save PNG charts to `charts/`

### Running a single platform
```bash
python3 -m benchmarks.bench_cognodb   # CognoDB only
python3 -m benchmarks.bench_neo4j    # Neo4j only
python3 -m benchmarks.bench_falkordb # FalkorDB only
python3 -m benchmarks.bench_memgraph # Memgraph only
python3 -m benchmarks.bench_kuzu     # Kuzu only

python3 analyze.py                    # re-generate table + charts from saved JSON
```

---

## 6. Results

> **Note:** The numbers below are placeholders. Run `./run_all.sh` to populate real results.  
> Actual results JSON files are in `results/` and charts are in `charts/`.

### 6.1 Data Loading

| Metric | CognoDB | Neo4j | FalkorDB | Memgraph | Kuzu |
|---|---|---|---|---|---|
| Nodes / sec | — | — | — | — | — |
| Edges / sec | — | — | — | — | — |
| Load time (s) | — | — | — | — | — |

### 6.2 Traversal Latency (ms)

| Hop depth | Stat | CognoDB | Neo4j | FalkorDB | Memgraph | Kuzu |
|---|---|---|---|---|---|---|
| 1-hop | p50 | — | — | — | — | — |
| 1-hop | p95 | — | — | — | — | — |
| 2-hop | p50 | — | — | — | — | — |
| 2-hop | p95 | — | — | — | — | — |
| 3-hop | p50 | — | — | — | — | — |
| 3-hop | p95 | — | — | — | — | — |

### 6.3 Lookup Latency (ms)

| Query | Stat | CognoDB | Neo4j | FalkorDB | Memgraph | Kuzu |
|---|---|---|---|---|---|---|
| Point lookup | p50 | — | — | — | — | — |
| Point lookup | p95 | — | — | — | — | — |
| Indexed lookup | p50 | — | — | — | — | — |
| Indexed lookup | p95 | — | — | — | — | — |

### 6.4 Aggregation Latency (ms)

| Query | Stat | CognoDB | Neo4j | FalkorDB | Memgraph | Kuzu |
|---|---|---|---|---|---|---|
| count(*) | p50 | — | — | — | — | — |
| count(*) | p95 | — | — | — | — | — |
| Group-by top-10 | p50 | — | — | — | — | — |
| Group-by top-10 | p95 | — | — | — | — | — |

### 6.5 Mixed Workload Throughput (QPS, 80 % reads / 20 % writes)

| Concurrency | CognoDB | Neo4j | FalkorDB | Memgraph | Kuzu |
|---|---|---|---|---|---|
| 10 clients | — | — | — | — | — |
| 40 clients | — | — | — | — | — |

### 6.6 Footprint

| Platform | Stored size | Source |
|---|---|---|
| CognoDB | not_observable | Free tier exposes no storage API |
| Neo4j | not_observable | Free tier exposes no storage API |
| FalkorDB | — | CALL db.info() |
| Memgraph | — | SHOW STORAGE INFO |
| Kuzu | — | Directory size on disk |

---

## 7. Analysis

> _Fill this section in after running the benchmarks with real numbers._

**Loading throughput** — Kuzu is expected to be the fastest loader because it uses `COPY FROM CSV` with a columnar bulk-import path that bypasses per-row transaction overhead. FalkorDB and Memgraph are both in-memory engines so their node creation is fast, but they still process edge inserts row-by-row. The cloud databases (CognoDB, Neo4j AuraDB) pay additional latency from the client–server round-trip for each batch.

**Traversal latency** — In-memory engines (Memgraph) should excel at 1-hop lookups because the full adjacency list lives in RAM. At 2- and 3-hop depths the branching factor of the email-Enron graph introduces significant variance between platforms: engines that precompute or cache path results (FalkorDB uses compressed adjacency matrices) may outperform those that evaluate lazily. The p95 numbers will reveal tail behaviour caused by hot hubs.

**Lookup** — A well-indexed lookup should be sub-millisecond on any platform for this dataset size. The interesting comparison is how much the index actually helps: platforms where the point-lookup scan is already fast (e.g. Memgraph with a fully in-memory layout) will show less relative speedup from indexing than disk-backed or cloud platforms.

**Aggregation** — `count(*)` over all edges tests full-scan throughput. Kuzu's columnar layout is designed for this and should win by a large margin. Group-by (top-10 by out-degree) is a more complex aggregation; expect Kuzu and Memgraph to be faster than the cloud platforms because of their in-process access patterns.

**Mixed workload** — FalkorDB is built on Redis which is single-threaded; throughput will plateau at ~1 concurrent writer regardless of client count. Kuzu uses MVCC with a single-writer lock; write-heavy mixes at 40 clients will expose the serialisation cost. Memgraph and Neo4j use multi-threaded write paths and should scale better. CognoDB's cloud-network round-trip will be the dominant factor for its mixed-workload numbers.

---

## 8. Caveats & Honest Notes

- **Network variance (cloud DBs):** CognoDB and Neo4j AuraDB are remote services. All latency numbers include client→cloud→client round-trip time. Running the benchmark from a machine co-located in the same cloud region would reduce this variance significantly.
- **Free-tier throttling:** Cloud free tiers may rate-limit or throttle burst workloads. If the mixed-workload numbers for CognoDB or Neo4j drop sharply at 40 clients, free-tier throttling is the likely cause — not a fundamental engine limitation.
- **FalkorDB single-threaded writes:** Redis (the underlying engine) processes commands serially. The mixed-workload write ratio is 20 %; at 40 concurrent clients the write QPS will be bounded by Redis's single-thread throughput, not the client concurrency. This is an architectural property, not a bug.
- **Kuzu embedded vs. server:** Kuzu runs in-process. It avoids all network overhead for query execution, making its latency numbers incomparable to the cloud databases for deployment scenarios. Kuzu's numbers are included because the assignment permits self-hosted deployments capped to equivalent resources, and it represents a genuinely different architectural approach worth documenting.
- **3-hop timeouts:** For nodes with high out-degree, a 3-hop traversal on this dataset can explore tens of thousands of paths. Some platforms may return results slowly or time out. Any such timeouts are recorded as errors in the JSON result files.
- **Warm numbers vs. cold numbers:** All reported numbers are warm (after 10 warm-up iterations). Cold-start latency is not separately measured in this run.
- **Results reproducibility:** Raw JSON results for each platform are in `results/`. Re-running `analyze.py` regenerates all tables and charts from those files.
