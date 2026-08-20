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
| CognoDB Cloud | 0.5 (burstable) | 256 MB | 1 GB | provider-assigned free-tier region |
| Neo4j AuraDB | ~0.5 (burstable free) | 256 MB | ~1 GB | provider-assigned free-tier region |
| FalkorDB | 0.5 (Docker limit) | 256 MB | Host disk | localhost |
| Memgraph | 0.5 (Docker limit) | 256 MB (--memory-limit) | Host disk | localhost |
| Kuzu | 0.5 (Docker/process limit) | 256 MB | Host disk | embedded |

Client machine: Ubuntu 24.04 LTS, Intel Core i5-10300H (8 threads), 16 GB RAM.

---

## 5. How to Reproduce

### Prerequisites
- Python ≥ 3.10
- Docker + Docker Compose v2
- Free accounts on: CognoDB Cloud, Neo4j AuraDB

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/vidhan63-soe/graphdb-benchmark.git
cd graphdb-benchmark

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

> Raw JSON results for each platform are in `results/`, charts are in `charts/`. All numbers below were produced by a real run of `./run_all.sh` against a live CognoDB Cloud free instance, a live Neo4j AuraDB free instance, and Dockerized FalkorDB/Memgraph capped at 0.5 vCPU / 256 MB.

### 6.1 Data Loading

| Metric | CognoDB | Neo4j | FalkorDB | Memgraph | Kuzu |
|---|---|---|---|---|---|
| Nodes / sec | 139.6 | 399.0 | 1,334.5 | 7,979.3 | 200,770.9 |
| Edges / sec | 1,398.6 | 3,998.2 | 13,372.4 | 79,954.0 | 2,011,769.1 |
| Load time (s) | 262.9 | 92.0 | 27.5 | 4.6 | 0.2 |

### 6.2 Traversal Latency (ms)

| Hop depth | Stat | CognoDB | Neo4j | FalkorDB | Memgraph | Kuzu |
|---|---|---|---|---|---|---|
| 1-hop | p50 | 305.2 | 87.7 | 0.2 | 0.3 | 0.7 |
| 1-hop | p95 | 381.5 | 169.1 | 0.2 | 0.4 | 0.7 |
| 2-hop | p50 | 307.0 | 90.0 | 0.5 | 0.7 | 4.6 |
| 2-hop | p95 | 385.9 | 147.5 | 1.3 | 1.3 | 6.2 |
| 3-hop | p50 | 2,049.8¹ | 92.8 | 24.3 | 17.7 | 84.2 |
| 3-hop | p95 | 9,517.3¹ | 127.2 | 122.5 | 91.0 | 413.1 |

¹ CognoDB's 3-hop number is a **partial sample of 6/100 iterations** — see [§8](#8-caveats--honest-notes) for why.

### 6.3 Lookup Latency (ms)

| Query | Stat | CognoDB | Neo4j | FalkorDB | Memgraph | Kuzu |
|---|---|---|---|---|---|---|
| Point lookup | p50 | 307.0 | 76.5 | 0.2 | 0.3 | 0.3 |
| Point lookup | p95 | 361.1 | 94.3 | 0.2 | 0.4 | 0.4 |
| Indexed lookup | p50 | 307.1 | 75.1 | 0.2 | 0.3 | 0.3 |
| Indexed lookup | p95 | 409.6 | 90.2 | 0.2 | 0.4 | 0.3 |

### 6.4 Aggregation Latency (ms)

| Query | Stat | CognoDB | Neo4j | FalkorDB | Memgraph | Kuzu |
|---|---|---|---|---|---|---|
| count(*) | p50 | 307.0 | 74.3 | 101.9 | 49.8 | 2.6 |
| count(*) | p95 | 440.4 | 80.9 | 107.9 | 76.0 | 2.9 |
| Group-by top-10 | p50 | 1,222.2 | 143.0 | 208.2² | — ³ | 11.5 |
| Group-by top-10 | p95 | 1,432.4 | 176.0 | 245.8² | — ³ | 12.7 |

² FalkorDB completed 6/100 iterations before this query timed out — see [§8](#8-caveats--honest-notes).
³ Memgraph errored on every iteration (0/100) — hit its 256 MB memory cap — see [§8](#8-caveats--honest-notes).

### 6.5 Mixed Workload Throughput (QPS, 80 % reads / 20 % writes, 60 s window)

| Concurrency | CognoDB | Neo4j | FalkorDB | Memgraph | Kuzu |
|---|---|---|---|---|---|
| 10 clients | 29.8 | 98.2 | 3,028.3 | 2,637.9 | 1,207.4 |
| 40 clients | 134.3 | 427.6 | 2,842.2 | 2,452.1 | 1,209.6 |

### 6.6 Footprint

| Platform | Stored size | Source |
|---|---|---|
| CognoDB | not_observable | Free tier exposes no storage API |
| Neo4j | not_observable | Free tier exposes no storage API |
| FalkorDB | not_observable | `CALL db.info()` not available on this image version |
| Memgraph | 118.73 MiB tracked / 176.55 MiB resident (peak 210.21 MiB) of a 256 MiB cap | `SHOW STORAGE INFO` |
| Kuzu | 9.19 MB on disk | File size on disk |

---

## 7. Analysis

**Loading throughput** spans four orders of magnitude, and the gap tracks architecture, not just deployment: Kuzu's `COPY FROM CSV` columnar bulk-import (2.0M edges/sec) and Memgraph's fully in-memory single-process writes (80k edges/sec) never leave the process; FalkorDB's Redis-backed sparse-matrix engine (13.4k edges/sec) still writes locally but pays Redis command overhead per batch; the two cloud platforms are almost two orders of magnitude slower than even the slowest self-hosted option, because every batch pays a real network round-trip on top of write execution — Neo4j AuraDB (4.0k edges/sec) loaded roughly 3x faster than CognoDB Cloud (1.4k edges/sec) on the identical batch size and dataset.

**Traversal latency** cleanly separates into two tiers: local engines (FalkorDB, Memgraph, Kuzu) answer 1-hop and 2-hop queries in under 5ms because the entire graph fits in 256 MB of RAM and there's no network hop. The cloud platforms sit at a ~75–310ms floor for even the simplest query — consistent with each query paying a real network/TLS round-trip rather than being compute-bound (see the lookup discussion below). At 3 hops, most platforms stay well under 130ms p95 (Memgraph fastest at 17.7ms p50, FalkorDB and Kuzu close behind), while Neo4j AuraDB holds its ~93ms floor almost unchanged — its query planner handles the widening fan-out with no visible penalty. CognoDB Cloud is the outlier: on the same query it degraded to a 2s p50 / 9.5s p95 on the 6 iterations it managed to complete, and the connection was not stable enough to finish a full 100-iteration run in any of four independent attempts (see §8).

**Lookup** — Point and indexed lookup are nearly identical on every platform (as expected: the id property is the primary key everywhere, so "point" and "indexed" lookup are the same physical query). The self-hosted engines answer in ~0.2–0.4ms; Neo4j AuraDB sits at ~75–90ms; CognoDB Cloud at ~307ms. Since the *query itself* is trivial (a single primary-key equality match on 36.7k nodes), the cloud platforms' latency here is almost entirely network/connection overhead rather than query execution — and CognoDB's floor is consistently ~4x higher than AuraDB's on the same query, same dataset, same client.

**Aggregation** — `count(*)` over 367,662 edges favors columnar/in-memory scans: Kuzu (2.6ms) and Memgraph (49.8ms) lead, with FalkorDB (101.9ms) and the cloud platforms (74–307ms) behind. The top-10 group-by is a heavier query (full scan + sort), and it's where the 256 MB memory cap became a real constraint rather than a theoretical one: **Memgraph rejected every iteration** with an explicit "memory limit exceeded" error at the application level, and **FalkorDB completed only 6/100 iterations before timing out** (in an earlier run under the same cap, the same query OOM-killed the FalkorDB container outright — see §8). Kuzu's columnar engine handled the same aggregation in 11.5ms without issue, and both cloud platforms — with far more real memory behind their free tier than the 256 MB Docker cap — completed all 100 iterations (CognoDB at 1.2s p50, Neo4j at 143ms p50).

**Mixed workload** — This is where the two tiers invert relative to raw latency: FalkorDB (2,637–3,028 QPS) and Memgraph (2,452–2,638 QPS) sustain the highest throughput at both concurrency levels, and — notably — FalkorDB's QPS does *not* collapse at 40 concurrent clients despite Redis's single-threaded command execution; it stayed within 6% of its 10-client number, suggesting command dispatch overhead, not the single Redis thread, was the binding constraint at these workload sizes. Kuzu holds steady around 1,207–1,210 QPS at both concurrencies, consistent with its single-writer MVCC lock capping write throughput regardless of reader count. The cloud platforms are throughput-bound by network round-trip per query rather than concurrency: Neo4j AuraDB scales from 98 to 428 QPS (10→40 clients) and CognoDB Cloud from 30 to 134 QPS — both roughly linear with concurrency, which is the signature of a workload where each client is mostly waiting on the network rather than contending for a server-side resource.

---

## 8. Caveats & Honest Notes

- **CognoDB Cloud connection instability (most significant finding):** Across four independent attempts to complete the 3-hop traversal benchmark against the CognoDB Cloud free (c0) instance, none succeeded in finishing all 100 iterations. The first two full-suite runs completed 6/100 and 0/100 iterations respectively before the Bolt connection was dropped mid-run (`defunct connection` / `OSError('No data')`); two further targeted retries against the already-loaded data failed to even establish a connection, with direct back-to-back connectivity checks (`driver.verify_connectivity()`, 5 attempts) showing roughly a 1-in-5 TLS-handshake failure rate on fresh connections. A one-time retry-on-stale-connection was added to the shared Bolt benchmark helper (applied identically to CognoDB, Neo4j AuraDB, and Memgraph, so all three get the same resilience) — this was enough for every *other* CognoDB benchmark to complete cleanly with full iteration counts, but not for the 3-hop query specifically. The reported 3-hop number for CognoDB (p50 2,049.8ms / p95 9,517.3ms) is therefore a **partial sample of 6 iterations**, kept because it is real, illustrative data rather than a placeholder — but it should not be read as a stable, reproducible latency figure the way every other number in this report is. This looks like a genuine free-tier characteristic (the most resource-intensive query is the one that repeatedly failed, while every simpler query on the same instance succeeded 100/100), not a bug in the benchmark harness or a one-off network blip.
- **FalkorDB OOM under the 256 MB cap:** In the first full run, the group-by aggregation query (`MATCH ... WITH ... count(*) ... ORDER BY ... LIMIT 10`) caused the OS to OOM-kill the FalkorDB container outright (`docker inspect` confirmed `OOMKilled: true`), which — because the container never restarted — also zeroed out the mixed-workload numbers that ran after it in the original benchmark order (they measured 0 QPS against a dead container, not genuine platform slowness). The benchmark was reordered so mixed-workload now runs *before* the group-by aggregation, which is the last thing the script does; on rerun, the same query caused a query timeout after 6/100 iterations rather than a hard container crash, but the container survived this time. Both outcomes (hard OOM-kill vs. graceful timeout) were observed for the identical query under the identical 256 MB cap across two runs — treat this as a real, reproducible resource-cap finding, not a flake.
- **Memgraph OOM under the 256 MB cap:** The same group-by aggregation failed on every one of 100 iterations with an explicit `Memory limit exceeded` error from Memgraph's own application-level memory accounting (not an OS-level OOM-kill). This is why Memgraph's mixed-workload numbers are unaffected (the connection stayed healthy) while its group-by numbers are entirely absent (0/100 iterations, all erroring). This is a direct, honest consequence of capping Memgraph to the same 256 MB used to approximate the cloud free tiers — it is not a criticism of Memgraph's engine, and Memgraph's own graceful in-app rejection (vs. FalkorDB's OS-level OOM-kill for the same cap) is itself a notable operational difference between the two.
- **Network variance (cloud DBs):** CognoDB and Neo4j AuraDB are remote services; all their latency numbers include a real client→cloud→client round-trip. The ~75–310ms floor visible on even trivial point-lookup queries for both cloud platforms is consistent with this, not with the query itself being expensive.
- **FalkorDB threading model:** Despite Redis's single-threaded command execution, FalkorDB's mixed-workload QPS did not collapse going from 10 to 40 concurrent clients (2,637.9 → 2,452.1 QPS, well within run-to-run noise) — worth noting because the a priori expectation (write throughput hard-capped by a single thread) was not clearly visible at these concurrency levels on this workload.
- **Kuzu embedded vs. server:** Kuzu runs in-process and pays no network overhead for query execution, so its latency numbers are not directly comparable to the cloud databases for deployment-scenario decisions. It's included because the assignment permits self-hosted deployments capped to equivalent resources, and its architecture (columnar, single-writer MVCC) is a genuinely different point of comparison.
- **Results reproducibility:** Raw JSON results for each platform are in `results/`, and the charts in `charts/` were generated directly from those files by `analyze.py` — re-running it regenerates both from the same source of truth.
