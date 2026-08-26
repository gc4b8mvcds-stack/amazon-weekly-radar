#!/usr/bin/env python3
"""Convert the V4.5 workbook's complete analysis sheet to web source JSON."""

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data-2.json"
SHEET = "全部机会分析"


def clean(value, default=""):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return default
    if hasattr(value, "item"):
        value = value.item()
    return value


def signature(row, detail=True):
    fields = ["机会等级", "趋势等级", "最终优先级", "趋势选品优先级", "实物选品适合度",
              "IP/品牌风险", "品牌搜索词", "季节类型", "趋势类型", "商品点击集中度", "品牌占位集中度"]
    if detail:
        fields += ["历史出现周数", "最近4周有效上涨次数", "连续有效上涨周数"]
    return tuple(clean(row.get(field)) for field in fields)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    args = parser.parse_args()
    frame = pd.read_excel(args.workbook, sheet_name=SHEET)
    if frame.empty:
        raise SystemExit(f"{SHEET} has no records")

    previous = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {}
    old_scores = {str(row.get("keyword", "")): float(row.get("score", 0)) for row in previous.get("records", [])}
    detailed, broad = defaultdict(list), defaultdict(list)
    for row in frame.to_dict("records"):
        keyword = str(clean(row.get("搜索词")))
        if keyword in old_scores:
            detailed[signature(row, True)].append(old_scores[keyword])
            broad[signature(row, False)].append(old_scores[keyword])

    records = []
    for row in frame.to_dict("records"):
        keyword = str(clean(row.get("搜索词")))
        candidates = detailed.get(signature(row, True)) or broad.get(signature(row, False))
        score = old_scores.get(keyword)
        if score is None and candidates:
            score = float(round(sum(candidates) / len(candidates)))
        if score is None:
            score = float({"S": 90, "A": 65, "B": 40}.get(clean(row.get("机会等级")), 30))
        records.append({
            "score": score, "keyword": keyword, "category": clean(row.get("来源类目")),
            "new_rank": clean(row.get("最新排名"), None), "old_rank": clean(row.get("上周排名"), None),
            "trend": clean(row.get("趋势类型")), "level": clean(row.get("机会等级")),
            "up4": clean(row.get("最近4周有效上涨次数"), 0), "product": clean(row.get("商品点击集中度")),
            "brand_conc": clean(row.get("品牌占位集中度")), "brand_search": clean(row.get("品牌搜索词")),
            "matched_brand": clean(row.get("匹配品牌")), "season": clean(row.get("季节类型")),
            "season_conf": clean(row.get("季节置信度"), 0), "season_reason": clean(row.get("季节命中依据")),
            "priority": clean(row.get("最终优先级")), "risk": clean(row.get("IP/品牌风险")),
            "fit": clean(row.get("实物选品适合度")),
        })

    records.sort(key=lambda x: (-x["score"], x["new_rank"] if isinstance(x["new_rank"], (int, float)) else 10**9, x["keyword"]))
    for pos, row in enumerate(records, 1):
        row["pos"] = pos
    categories = sorted({part.strip() for row in records for part in str(row["category"]).split(",") if part.strip()})
    payload = {"version": "V4.5", "date": max(str(clean(v))[:10] for v in frame["最新日期"]),
               "copyright": "飞羽电竞", "categories": categories, "records": records}
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Imported {len(records)} records from {args.workbook.name}")
    print("Categories:", " / ".join(categories))


if __name__ == "__main__":
    main()
