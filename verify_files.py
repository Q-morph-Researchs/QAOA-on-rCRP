"""Check every file against MANIFEST_SHA256.json. Run: python3 verify_files.py"""
import hashlib, json, sys
from pathlib import Path
root = Path(__file__).resolve().parent
manifest = json.loads((root / "MANIFEST_SHA256.json").read_text())
bad = [p for p, h in manifest.items()
       if not (root / p).is_file() or hashlib.sha256((root / p).read_bytes()).hexdigest() != h]
print(f"Checked {len(manifest)} files; mismatches: {len(bad)}")
for p in bad:
    print("  ", p)
sys.exit(1 if bad else 0)
