#!/usr/bin/env python3
"""Load email-Enron dataset into Neo4j AuraDB (free tier)."""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
from loaders.bolt_loader import load_graph

load_dotenv()

if __name__ == "__main__":
    uri = os.environ["NEO4J_URI"]
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ["NEO4J_PASSWORD"]

    result = load_graph(uri, user, password, "Neo4j")
    print(json.dumps(result, indent=2))
