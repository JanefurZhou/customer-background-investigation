#!/usr/bin/env python3
"""背调台账：按客户建档、历史版本对比、到期复查提醒（零第三方依赖，CSV 存储）。

用法:
    # 记录一次背调（读 risk_score.py 的 JSON 输出，再补充客户字段）
    python3 scripts/risk_score.py input.json > score.json
    python3 scripts/dd_ledger.py add --score score.json --company "Example Ltd" --country GB \
        --reg-no 01234567 --domain example.com --report DD_Example_20261019.md --review-days 90
    python3 scripts/dd_ledger.py history --company "Example Ltd"      # 该客户全部背调记录
    python3 scripts/dd_ledger.py diff --company "Example Ltd"         # 最近两次的变化
    python3 scripts/dd_ledger.py due [--today 2026-12-31]             # 到期需复查的客户
    python3 scripts/dd_ledger.py --selftest
默认台账文件 dd_ledger.csv（当前目录），可用 --ledger 指定。只追加，不覆盖历史记录。
"""
import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import tempfile

FIELDS = ["company_key", "company", "country", "reg_no", "domain", "dd_date", "dd_mode", "weights",
          "dd_rating", "dd_score", "confidence", "vetoes", "missing", "dd_blockers", "dd_next_review",
          "report_file", "analyst", "notes"]
DIFF_FIELDS = ["dd_rating", "dd_score", "confidence", "vetoes", "missing", "dd_blockers", "country",
               "reg_no", "domain", "dd_mode", "weights"]


def key_of(name):
    n = name.lower()
    n = re.sub(r"[^a-z0-9\u0400-\u04ff\u0600-\u06ff\u4e00-\u9fff]+", " ", n)
    n = re.sub(r"\b(limited|ltd|llc|inc|gmbh|co|corp|plc|sa|srl|bv|jsc|pte|sdn bhd|company)\b", " ", n)
    return re.sub(r"\s+", "-", n.strip())


def load(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def append(path, row):
    new = not os.path.exists(path)
    with open(path, "a", encoding="utf-8-sig" if new else "utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in FIELDS})


def make_row(score, company, country="", reg_no="", domain="", report="", analyst="", notes="",
             review_days=90, date=None):
    date = date or dt.date.today().isoformat()
    rating = score.get("rating", "")
    days = review_days
    if "🔴" in rating:
        days = min(days, 30)
    return {
        "company_key": key_of(company), "company": company, "country": country, "reg_no": reg_no,
        "domain": domain, "dd_date": date, "dd_mode": score.get("mode", ""),
        "weights": score.get("weights", "default"), "dd_rating": rating,
        "dd_score": "" if score.get("score") is None else score["score"],
        "confidence": score.get("confidence", ""), "vetoes": "；".join(score.get("vetoes", [])),
        "missing": "；".join(score.get("missing", [])),
        "dd_blockers": score.get("trade_blocker_note", "") if score.get("trade_blocker") else "",
        "dd_next_review": (dt.date.fromisoformat(date) + dt.timedelta(days=days)).isoformat(),
        "report_file": report, "analyst": analyst, "notes": notes,
    }


def history(rows, company):
    k = key_of(company)
    return sorted([r for r in rows if r["company_key"] == k], key=lambda r: r["dd_date"])


def diff(rows, company):
    h = history(rows, company)
    if len(h) < 2:
        return None
    a, b = h[-2], h[-1]
    changes = [(f, a.get(f, ""), b.get(f, "")) for f in DIFF_FIELDS if a.get(f, "") != b.get(f, "")]
    alerts = []
    order = ["🟢", "🟡", "🔴"]
    ra = next((i for i, x in enumerate(order) if x in a["dd_rating"]), None)
    rb = next((i for i, x in enumerate(order) if x in b["dd_rating"]), None)
    if ra is not None and rb is not None and rb > ra:
        alerts.append("⚠️ 评级变差：" + a["dd_rating"] + " → " + b["dd_rating"])
    if a.get("domain") and b.get("domain") and a["domain"] != b["domain"]:
        alerts.append("⚠️ 联系域名变化：先确认不是冒充或账户劫持")
    if a.get("reg_no") and b.get("reg_no") and a["reg_no"] != b["reg_no"]:
        alerts.append("⚠️ 注册号变化：主体可能已更换，需重新核验签约主体")
    if b.get("vetoes") and not a.get("vetoes"):
        alerts.append("⚠️ 新出现一票否决项：" + b["vetoes"])
    return {"company": b["company"], "from": a["dd_date"], "to": b["dd_date"], "changes": changes, "alerts": alerts}


def due(rows, today):
    latest = {}
    for r in rows:
        if r["company_key"] not in latest or r["dd_date"] >= latest[r["company_key"]]["dd_date"]:
            latest[r["company_key"]] = r
    out = [r for r in latest.values() if r.get("dd_next_review") and r["dd_next_review"] <= today]
    return sorted(out, key=lambda r: r["dd_next_review"])


def selftest():
    fails = 0
    def check(name, cond):
        nonlocal fails
        fails += not cond
        print(("PASS " if cond else "FAIL ") + name)
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, "l.csv")
        s1 = {"mode": "quick", "rating": "🟢 低风险", "score": None, "confidence": "正常", "vetoes": [], "missing": []}
        s2 = {"mode": "deep", "rating": "🟡 中风险", "score": 42.5, "confidence": "正常", "vetoes": [], "missing": ["财务信用"]}
        append(p, make_row(s1, "Example Trading Ltd", "GB", "123", "example.com", date="2026-07-01"))
        append(p, make_row(s2, "EXAMPLE TRADING LIMITED", "GB", "123", "examp1e.com", date="2026-10-01"))
        append(p, make_row({"mode": "quick", "rating": "🔴 高风险", "score": None, "vetoes": ["制裁/出口管制命中"]},
                           "Other Co", "RU", date="2026-10-10", review_days=90))
        rows = load(p)
        check("同一客户不同写法归档到一起", len(history(rows, "Example Trading Ltd")) == 2)
        d = diff(rows, "Example Trading")
        check("识别评级变差", d and any("评级变差" in x for x in d["alerts"]))
        check("识别域名变化", d and any("域名变化" in x for x in d["alerts"]))
        check("红色客户复查期 ≤30 天", load(p)[2]["dd_next_review"] == "2026-11-09")
        check("到期提醒", [r["company"] for r in due(rows, "2026-11-30")] == ["Other Co"])
        check("只追加不覆盖", len(rows) == 3)
        check("单条记录无法对比", diff(rows, "Other Co") is None)
    print("\n全部通过" if not fails else f"\n{fails} 项失败")
    return fails


def main():
    if "--selftest" in sys.argv:
        sys.exit(1 if selftest() else 0)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["add", "history", "diff", "due"])
    ap.add_argument("--ledger", default="dd_ledger.csv")
    ap.add_argument("--score", help="risk_score.py 输出的 JSON 文件")
    ap.add_argument("--company")
    ap.add_argument("--country", default="")
    ap.add_argument("--reg-no", default="")
    ap.add_argument("--domain", default="")
    ap.add_argument("--report", default="")
    ap.add_argument("--analyst", default="")
    ap.add_argument("--notes", default="")
    ap.add_argument("--review-days", type=int, default=90)
    ap.add_argument("--today", default=dt.date.today().isoformat())
    a = ap.parse_args()
    rows = load(a.ledger)
    if a.cmd == "add":
        if not (a.score and a.company):
            ap.error("add 需要 --score 和 --company")
        with open(a.score, encoding="utf-8") as f:
            score = json.load(f)
        row = make_row(score, a.company, a.country, a.reg_no, a.domain, a.report, a.analyst, a.notes, a.review_days)
        append(a.ledger, row)
        print(f"已记录：{row['company']} {row['dd_rating']}，下次复查 {row['dd_next_review']}")
        d = diff(load(a.ledger), a.company)
        if d and d["alerts"]:
            print("\n".join(d["alerts"]))
    elif a.cmd == "history":
        for r in history(rows, a.company or ""):
            print(f"{r['dd_date']}  {r['dd_mode']:<5} {r['dd_rating']:<8} {r['dd_score']:<6} {r['report_file']}")
    elif a.cmd == "diff":
        d = diff(rows, a.company or "")
        if not d:
            print("记录少于 2 条，无法对比")
        else:
            print(f"{d['company']}：{d['from']} → {d['to']}")
            for f, x, y in d["changes"]:
                print(f"  {f}: {x or '—'} → {y or '—'}")
            for al in d["alerts"]:
                print(al)
    elif a.cmd == "due":
        items = due(rows, a.today)
        if not items:
            print("没有到期需要复查的客户")
        for r in items:
            print(f"{r['dd_next_review']}  {r['company']}  {r['dd_rating']}  上次 {r['dd_date']}")


if __name__ == "__main__":
    main()
