#!/usr/bin/env python3
import base64
import gzip
import argparse
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", nargs="?", type=Path)
    args = parser.parse_args()
    source = json.loads((ROOT / "data-2.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    records = source["records"]
    assert manifest["web_arch"] == "v2"
    assert manifest["summary"]["total"] == len(records)
    assert manifest["chunk_count"] == len(manifest["chunks"])
    loaded = []
    for chunk in manifest["chunks"]:
        assert chunk["encoding"] == "gzip-base64"
        encoded = (ROOT / chunk["path"]).read_text(encoding="ascii")
        rows = json.loads(gzip.decompress(base64.b64decode(encoded)))["records"]
        assert len(rows) == chunk["count"]
        assert rows[0]["pos"] == chunk["start"]
        assert rows[-1]["pos"] == chunk["end"]
        loaded.extend(rows)
    assert loaded == records
    categories = sorted({c.strip() for row in records for c in re.split(r"[,，;；]", row["category"]) if c.strip()})
    assert categories == manifest["categories"]
    assert all(not re.search(r"[,，;；]", category) for category in manifest["categories"])
    assert manifest["date"] == "2026-08-29"
    assert manifest["generated_at"] == manifest["updated_at"]
    assert manifest["updated_at"].endswith("+08:00")
    assert "DecompressionStream(\"gzip\")" in (ROOT / "index.html").read_text(encoding="utf-8")

    if args.workbook:
        frame = pd.read_excel(args.workbook, sheet_name="全部机会分析")
        workbook_rows = [
            (str(keyword), str(category))
            for keyword, category in zip(frame["搜索词"], frame["来源类目"])
        ]
        web_rows = [(str(row["keyword"]), str(row["category"])) for row in records]
        assert len(frame) == len(records)
        assert set(workbook_rows) == set(web_rows)
        workbook_categories = sorted({
            part.strip()
            for value in frame["来源类目"].dropna().astype(str)
            for part in re.split(r"[,，;；]", value)
            if part.strip()
        })
        assert workbook_categories == manifest["categories"]
        workbook_date = max(frame["最新日期"].dropna().astype(str).str[:10])
        assert workbook_date == manifest["date"]
        assert all(
            all(part.strip() in manifest["categories"] for part in re.split(r"[,，;；]", row["category"]) if part.strip())
            for row in records
        )
    print(f"Validated {len(records)} records in {len(manifest['chunks'])} chunks")


if __name__ == "__main__":
    main()
