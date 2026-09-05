#!/usr/bin/env python3
import base64
import gzip
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data-2.json"
MANIFEST = ROOT / "manifest.json"
CHUNK_SIZE = 200


def category_parts(value):
    return [part.strip() for part in re.split(r"[,，;；]", str(value or "")) if part.strip()]


def main():
    src = json.loads(SOURCE.read_text(encoding="utf-8"))
    records = src.get("records", [])
    if not records:
        raise SystemExit("data-2.json has no records")

    records = sorted(records, key=lambda x: int(x.get("pos") or 10**9))

    # 自动发现单一类目；跨类目记录会拆开加入菜单。
    categories = sorted({category for row in records for category in category_parts(row.get("category"))})

    summary = {
        "total": len(records),
        "trend_up": sum(1 for x in records if x.get("trend") == "持续上涨"),
        "brand_yes": sum(1 for x in records if x.get("brand_search") == "是"),
        "seasonal": sum(1 for x in records if x.get("season") not in (None, "", "常规", "待确认")),
        "review": sum(1 for x in records if x.get("season") == "待确认"),
    }

    for old in ROOT.glob("data-*.json.gz.b64"):
        old.unlink()

    chunks = []
    for n, start in enumerate(range(0, len(records), CHUNK_SIZE), 1):
        part = records[start:start + CHUNK_SIZE]
        filename = f"data-{n:03d}.json.gz.b64"
        path = ROOT / filename
        raw = json.dumps({"records": part}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        path.write_text(base64.b64encode(gzip.compress(raw, mtime=0)).decode("ascii"), encoding="ascii")
        chunks.append({
            "path": filename,
            "start": int(part[0].get("pos") or start + 1),
            "end": int(part[-1].get("pos") or start + len(part)),
            "count": len(part),
            "encoding": "gzip-base64",
        })

    generated_at = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")
    manifest = {
        "version": src.get("version", "V4.5"),
        "web_arch": "v2",
        "date": src.get("date", ""),
        "generated_at": generated_at,
        "updated_at": generated_at,
        "copyright": src.get("copyright", "飞羽电竞"),
        "summary": summary,
        "categories": categories,
        "chunk_size": CHUNK_SIZE,
        "chunk_count": len(chunks),
        "chunks": chunks,
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    # 发布前完整校验。
    total = 0
    for item in chunks:
        p = ROOT / item["path"]
        d = json.loads(gzip.decompress(base64.b64decode(p.read_text(encoding="ascii"))))
        total += len(d.get("records", []))
    if total != len(records):
        raise SystemExit(f"chunk validation failed: {total} != {len(records)}")

    print(f"V2 build OK: {len(records)} records, {len(chunks)} chunks")
    print("Categories:", " / ".join(categories))
    print("Generated at:", generated_at)


if __name__ == "__main__":
    main()
