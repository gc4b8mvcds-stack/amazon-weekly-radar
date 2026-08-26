#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = json.loads((ROOT / "data-2.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    records = source["records"]
    assert manifest["web_arch"] == "v2"
    assert manifest["summary"]["total"] == len(records)
    assert manifest["chunk_count"] == len(manifest["chunks"])
    loaded = []
    for chunk in manifest["chunks"]:
        rows = json.loads((ROOT / chunk["path"]).read_text(encoding="utf-8"))["records"]
        assert len(rows) == chunk["count"]
        assert rows[0]["pos"] == chunk["start"]
        assert rows[-1]["pos"] == chunk["end"]
        loaded.extend(rows)
    assert loaded == records
    categories = sorted({c.strip() for row in records for c in row["category"].split(",") if c.strip()})
    assert categories == manifest["categories"]
    assert all("," not in category for category in manifest["categories"])
    print(f"Validated {len(records)} records in {len(manifest['chunks'])} chunks")


if __name__ == "__main__":
    main()
