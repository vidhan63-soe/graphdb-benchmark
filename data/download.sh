#!/usr/bin/env bash
# Downloads the SNAP email-Enron dataset and prepares normalized CSV files.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DATASET_URL="https://snap.stanford.edu/data/email-Enron.txt.gz"
RAW_FILE="email-Enron.txt.gz"

if [ -f "$RAW_FILE" ]; then
    echo "[data] Raw file already present, skipping download."
else
    echo "[data] Downloading email-Enron dataset from SNAP..."
    curl -L -o "$RAW_FILE" "$DATASET_URL"
    echo "[data] Download complete."
fi

if [ -f "nodes.csv" ] && [ -f "edges.csv" ] && [ -f "start_nodes.txt" ]; then
    echo "[data] Prepared files already exist, skipping prepare step."
else
    echo "[data] Preparing normalized CSV files..."
    python3 prepare.py
fi

echo "[data] Ready."
