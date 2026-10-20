#!/usr/bin/env python3
"""海关进口记录量化（零依赖）。

把 ImportYeti / 52wmb 等导出的进口提单记录整理成 CSV，输出：
总票数、时间跨度、最近一票及距今天数、每票平均 TEU、月均 TEU、
供应国与供应商占比、HS 品类、采购间隔中位数、预计下次采购窗口（推断）、规模分档，
以及自动信号：进口中断、单一供应商依赖、新品类、样本少。

CSV 表头不区分大小写，支持以下别名：
  date      : date, arrival_date, shipment_date, 日期, 到港日期
  origin    : origin, country, origin_country, 供应国, 起运国
  supplier  : supplier, shipper, 供应商, 发货人
  hs        : hs, hs_code, hscode, HS编码
  teu       : teu, containers, 柜量, TEU
  product   : product, description, 品名, 货物描述

用法：
    python3 scripts/customs_summary.py shipments.csv
    python3 scripts/customs_summary.py shipments.csv --inquiry-hs 6301,5806 --md
    python3 scripts/customs_summary.py shipments.csv --today 2026-10-21
    python3 scripts/customs_summary.py --selftest

说明：所有"预计下次采购"都是基于历史间隔的推断，报告里必须写"推断"。
"""
import argparse
import csv
import datetime as dt
import io
import json
import statistics
import sys
from collections import Counter

ALIASES = {
    "date": ["date", "arrival_date", "shipment_date", "arrival date", "日期", "到港日期"],
    "origin": ["origin", "country", "origin_country", "origin country", "供应国", "起运国"],
    "supplier": ["supplier", "shipper", "供应商", "发货人"],
    "hs": ["hs", "hs_code", "hscode", "hs code", "hs编码"],
    "teu": ["teu", "containers", "柜量"],
    "product": ["product", "description", "品名", "货物描述"],
}


def _map_header(fields):
    m = {}
    for f in fields or []:
        k = (f or "").strip().lower()
        for std, al in ALIASES.items():
            if k in al and std not in m:
                m[std] = f
    return m


def _date(s):
    s = (s or "").strip()[:10]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d.%m.%Y"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def _float(s):
    try:
        return float(str(s).strip())
    except (TypeError, ValueError):
        return None


def load(text):
    rd = csv.DictReader(io.StringIO(text))
    hm = _map_header(rd.fieldnames)
    if "date" not in hm:
        raise ValueError("CSV 缺少日期列（date / arrival_date / 日期）")
    rows = []
    for r in rd:
        d = _date(r.get(hm["date"]))
        if not d:
            continue
        rows.append({
            "date": d,
            "origin": (r.get(hm.get("origin", ""), "") or "").strip() or "未知",
            "supplier": (r.get(hm.get("supplier", ""), "") or "").strip() or "未知",
            "hs": "".join(c for c in (r.get(hm.get("hs", ""), "") or "") if c.isdigit())[:6],
            "teu": _float(r.get(hm.get("teu", ""), "")),
            "product": (r.get(hm.get("product", ""), "") or "").strip(),
        })
    rows.sort(key=lambda x: x["date"])
    return rows


def _share(counter, n):
    return [(k, v, round(100 * v / n)) for k, v in counter.most_common(3)]


def summarize(rows, today=None, inquiry_hs=None):
    today = today or dt.date.today()
    n = len(rows)
    out = {"shipments": n, "signals": []}
    if n == 0:
        out["signals"].append(("ℹ️", "没有可用记录：海关数据写\"未获取\"，不代表对方没有进口"))
        return out
    first, last = rows[0]["date"], rows[-1]["date"]
    span_days = max((last - first).days, 1)
    months = max(span_days / 30.44, 1)
    teus = [r["teu"] for r in rows if r["teu"] is not None]
    total_teu = sum(teus) if teus else None
    gaps = [(b["date"] - a["date"]).days for a, b in zip(rows, rows[1:]) if (b["date"] - a["date"]).days > 0]
    med = statistics.median(gaps) if gaps else None
    since = (today - last).days
    monthly_teu = round(total_teu / months, 2) if total_teu is not None else None
    if monthly_teu is None:
        tier = "未获取（缺 TEU 列）"
    elif monthly_teu < 0.5:
        tier = "小批量"
    elif monthly_teu <= 3:
        tier = "中等"
    else:
        tier = "大货"
    hs_counter = Counter(r["hs"][:4] for r in rows if r["hs"])
    out.update({
        "first": first.isoformat(), "last": last.isoformat(), "days_since_last": since,
        "avg_teu": round(total_teu / len(teus), 2) if teus else None,
        "monthly_teu": monthly_teu, "tier": tier,
        "origins": _share(Counter(r["origin"] for r in rows), n),
        "suppliers": _share(Counter(r["supplier"] for r in rows), n),
        "hs4": hs_counter.most_common(5),
        "median_gap_days": med,
        "next_window": None,
    })
    if med:
        nxt = last + dt.timedelta(days=int(med))
        lo, hi = nxt - dt.timedelta(days=int(med * 0.25)), nxt + dt.timedelta(days=int(med * 0.25))
        out["next_window"] = f"{lo.isoformat()} ~ {hi.isoformat()}（推断）"
    if n < 3:
        out["signals"].append(("ℹ️", f"样本少（{n} 票）：统计结论只作参考"))
    if med and since > 2 * med and since > 180:
        out["signals"].append(("🟡", f"进口中断：距最近一票 {since} 天，超过采购间隔中位数（{int(med)} 天）的 2 倍，追问原因"))
    top_sup = out["suppliers"][0]
    if n >= 3 and top_sup[2] > 70:
        out["signals"].append(("ℹ️", f"单一供应商依赖：{top_sup[0]} 占 {top_sup[2]}%，切入难度较高"))
    if inquiry_hs:
        hist = {r["hs"] for r in rows if r["hs"]}
        missing = [h for h in inquiry_hs if not any(x.startswith(h[:4]) for x in hist)]
        if missing:
            out["signals"].append(("ℹ️", f"新品类：询盘品类 {','.join(missing)} 不在历史进口记录里，无历史采购可参照"))
    return out


def to_md(s):
    if s["shipments"] == 0:
        return "| 进口记录 | 未获取 |\n|---|---|\n" + "\n".join(f"\n- {a} {b}" for a, b in s["signals"])
    fmt = lambda lst: "；".join(f"{k} {p}%" for k, _, p in lst)
    lines = [
        "| 项目 | 结果 |", "|---|---|",
        f"| 总票数 / 时间跨度 | {s['shipments']} 票，{s['first']} ~ {s['last']} |",
        f"| 最近一票 | {s['last']}（距今 {s['days_since_last']} 天） |",
        f"| 每票平均 TEU / 月均 TEU | {s['avg_teu'] if s['avg_teu'] is not None else '未获取'} / {s['monthly_teu'] if s['monthly_teu'] is not None else '未获取'} |",
        f"| 规模分档 | {s['tier']} |",
        f"| 供应国占比（前 3） | {fmt(s['origins'])} |",
        f"| 供应商占比（前 3） | {fmt(s['suppliers'])} |",
        f"| HS 品类（4 位） | {'、'.join(f'{k}×{v}' for k, v in s['hs4']) or '未获取'} |",
        f"| 采购间隔中位数 | {str(int(s['median_gap_days'])) + ' 天' if s['median_gap_days'] else '未获取'} |",
        f"| 预计下次采购窗口 | {s['next_window'] or '未获取'} |",
    ]
    if s["signals"]:
        lines.append("")
        lines += [f"- {a} {b}" for a, b in s["signals"]]
    return "\n".join(lines)


def _selftest():
    T = dt.date(2026, 10, 21)
    csv1 = "Arrival Date,Country,Shipper,HS Code,TEU\n" + "\n".join(
        f"2025-{m:02d}-10,China,Mill A,630140,0.2" for m in range(1, 13, 2)) + "\n2025-11-20,India,Mill B,580610,0.1\n"
    csv2 = "日期,供应国,供应商,HS编码,柜量\n2023-01-05,越南,厂甲,6301,2\n2023-02-05,越南,厂甲,6301,2\n2023-03-07,越南,厂甲,6301,2\n2023-04-06,越南,厂甲,6301,2\n"
    csv3 = "date,origin,supplier,hs,teu\n" + "\n".join(f"2026-{m:02d}-01,China,Big Co,940490,5" for m in range(1, 11))
    s1 = summarize(load(csv1), T, ["6301", "6006"])
    s2 = summarize(load(csv2), T)
    s3 = summarize(load(csv3), T)
    s0 = summarize([], T)
    cases = [
        ("英文表头别名可识别", s1["shipments"] == 7),
        ("月均 TEU < 0.5 → 小批量", s1["tier"] == "小批量"),
        ("询盘品类不在历史里 → 新品类信号", any("6006" in b for _, b in s1["signals"])),
        ("中文表头可识别 + 单一供应商依赖", s2["shipments"] == 4 and any("单一供应商" in b for _, b in s2["signals"])),
        ("停了 3 年 → 进口中断", any("进口中断" in b for _, b in s2["signals"])),
        ("月均 TEU > 3 → 大货", s3["tier"] == "大货"),
        ("近期稳定采购 → 不报进口中断", not any("进口中断" in b for _, b in s3["signals"])),
        ("预计下次采购窗口标注推断", "推断" in (s3["next_window"] or "")),
        ("无记录 → 未获取，不判没有进口", s0["shipments"] == 0 and "未获取" in s0["signals"][0][1]),
        ("Markdown 输出含规模分档", "规模分档" in to_md(s1)),
    ]
    fails = 0
    for name, ok in cases:
        fails += not ok
        print(("PASS " if ok else "FAIL ") + name)
    print("\n全部通过" if not fails else f"\n{fails} 项失败")
    return fails


def main():
    ap = argparse.ArgumentParser(description="海关进口记录量化")
    ap.add_argument("csv", nargs="?")
    ap.add_argument("--inquiry-hs", help="询盘品类 HS 编码，逗号分隔")
    ap.add_argument("--today", help="统计基准日 YYYY-MM-DD，默认今天")
    ap.add_argument("--md", action="store_true", help="输出 Markdown 表格")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(1 if _selftest() else 0)
    if not a.csv:
        ap.error("需要 CSV 文件，或用 --selftest")
    with open(a.csv, encoding="utf-8-sig", errors="ignore") as f:
        rows = load(f.read())
    today = _date(a.today) if a.today else None
    hs = [h.strip() for h in a.inquiry_hs.split(",")] if a.inquiry_hs else None
    s = summarize(rows, today, hs)
    print(to_md(s) if a.md else json.dumps(s, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
