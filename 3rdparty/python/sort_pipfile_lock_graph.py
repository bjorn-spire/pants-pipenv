#!/usr/bin/env python3

import json
import sys
from typing import Any, Dict, List

if len(sys.argv) == 1:
    input_file = "Pipfile.lock.graph"
else:
    input_file = sys.argv[1]

with open(input_file) as f:
    input_obj: List[Dict[str, Any]] = json.load(f)

input_obj.sort(key=lambda obj: obj["package"]["key"])
for package in input_obj:
    package["dependencies"].sort(key=lambda obj: obj["key"])

with open(input_file, "w") as f:
    json.dump(input_obj, f, indent=4)
