#!/usr/bin/env python3
"""Load email-Enron dataset into CognoDB Cloud (free c0 tier)."""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
from loaders.bolt_loader import load_graph

load_dotenv()

if __name__ == "__main__":
    uri = os.environ["COGNODB_URI"]
    user = os.environ.get("COGNODB_USER", "cognodb")
    password = os.environ["COGNODB_PASSWORD"]

    result = load_graph(uri, user, password, "CognoDB")
    print(json.dumps(result, indent=2))
