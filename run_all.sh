#!/usr/bin/env bash
# One-command benchmark runner.
# Usage: ./run_all.sh
# Requires: .env file with credentials (copy .env.example and fill in values).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

log() { echo -e "\n\033[1;34m>>> $*\033[0m"; }
err() { echo -e "\033[1;31m[ERROR] $*\033[0m" >&2; }

# ── Preflight ──────────────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    err ".env file not found. Copy .env.example → .env and fill in your credentials."
    exit 1
fi

if ! python3 -c "import neo4j, falkordb, kuzu, numpy, pandas, matplotlib, tqdm, dotenv, tabulate" 2>/dev/null; then
    log "Installing Python dependencies …"
    pip install -r requirements.txt
fi

# ── Dataset ────────────────────────────────────────────────────────────────────
log "Step 1/5 — Prepare dataset"
bash data/download.sh

# ── Docker services (FalkorDB + Memgraph) ──────────────────────────────────────
log "Step 2/5 — Start Docker services (FalkorDB + Memgraph)"
docker compose up -d falkordb memgraph

log "Waiting for FalkorDB …"
until docker compose exec -T falkordb redis-cli ping 2>/dev/null | grep -q PONG; do
    sleep 1
done

log "Waiting for Memgraph …"
until echo "RETURN 1;" | docker compose exec -T memgraph mgconsole 2>/dev/null; do
    sleep 2
done

# ── Cloud DB benchmarks ────────────────────────────────────────────────────────
log "Step 3/5 — CognoDB Cloud benchmark"
python3 -m benchmarks.bench_cognodb

log "Step 3/5 — Neo4j AuraDB benchmark"
python3 -m benchmarks.bench_neo4j

# ── Self-hosted benchmarks ─────────────────────────────────────────────────────
log "Step 4/5 — FalkorDB benchmark"
python3 -m benchmarks.bench_falkordb

log "Step 4/5 — Memgraph benchmark"
python3 -m benchmarks.bench_memgraph

log "Step 4/5 — Kuzu benchmark"
python3 -m benchmarks.bench_kuzu

# ── Analysis ──────────────────────────────────────────────────────────────────
log "Step 5/5 — Generate results table + charts"
python3 analyze.py

log "All done! Results in results/  |  Charts in charts/"
