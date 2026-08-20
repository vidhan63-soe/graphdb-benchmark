#!/usr/bin/env python3
"""Load email-Enron dataset into Memgraph (Docker, resource-capped)."""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
from loaders.bolt_loader import load_graph

load_dotenv()

if __name__ == "__main__":
    uri = os.environ.get("MEMGRAPH_URI", "bolt://localhost:7688")
    user = os.environ.get("MEMGRAPH_USER", "")
    password = os.environ.get("MEMGRAPH_PASSWORD", "")

    result = load_graph(uri, user, password, "Memgraph")
    print(json.dumps(result, indent=2))
