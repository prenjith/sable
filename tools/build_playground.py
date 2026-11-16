#!/usr/bin/env python3
"""Build the browser playground with the current sable.py embedded."""

import json
import pathlib

root = pathlib.Path(__file__).resolve().parent.parent
source = (root / "sable.py").read_text()
template = (root / "tools" / "playground_template.html").read_text()
output = template.replace("__SABLE_SOURCE__", json.dumps(source))
(root / "docs" / "playground.html").write_text(output)
print("wrote docs/playground.html")
