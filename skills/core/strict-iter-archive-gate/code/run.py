#!/usr/bin/env python3
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from strictiterarchivegate import run

if __name__ == "__main__":
    import json
    payload = run(sys.argv[1] if len(sys.argv) > 1 else "")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
