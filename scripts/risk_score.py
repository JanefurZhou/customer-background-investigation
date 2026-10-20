#!/usr/bin/env python3
"""跨境客户背调风险评分（零第三方依赖）。

用法:
    python3 scripts/risk_score.py input.json          # 输出 JSON
    python3 scripts/risk_score.py input.json --md     # 输出 Markdown 风险矩阵
    python3 scripts/risk_score.py --selftest          # 运行内置回归测试

输入 JSON:
{
  "company": "Example Ltd",
  "mode": "deep",                       # deep | quick
  "scores": {                           # 0-10，查不到填 null
    "sanctions": 0, "litigation": 3, "identity": 0, "financial": null,
    "stability": 5, "digital": 3, "trade": 3
  },
  "vetoes": {                           # 任一为 true 直接判高风险
    "sanctions_hit": false,             # 制裁/出口管制命中且未排除同名
    "identity_fake": false,             # 身份无法核验或证件虚假
    "bankruptcy": false,                # 破产/清算
    "fraud_confirmed": false            # 已确认欺诈信号
  },
  "trade_blocker": false,               # 品类在目的国不可按现方案交易
  "trade_blocker_note": "",
  "weights": "default"                  # 可选：预设名，或 {维度: 权重} 自定义（7 个维度齐全、合计 1、制裁 ≥ 0.20）
}

预设权重（python3 scripts/risk_score.py --presets 查看）：
  default      通用外贸
  project_b2b  项目型 B2B（建材/工程/设备）：经营年限、诉讼更重要
  ecommerce    跨境电商/零售卖家：数字口碑更重要
"""
import json
import sys

WEIGHTS = {
    "sanctions": 0.25, "litigation": 0.15, "identity": 0.15, "financial": 0.15,
    "stability": 0.10, "digital": 0.10, "trade": 0.10,
}
PRESETS = {
    "default": dict(WEIGHTS),
    "project_b2b": {"sanctions": 0.25, "litigation": 0.20, "identity": 0.15, "financial": 0.10,
                    "stability": 0.15, "digital": 0.05, "trade": 0.10},
    "ecommerce": {"sanctions": 0.25, "litigation": 0.10, "identity": 0.15, "financial": 0.10,
                  "stability": 0.10, "digital": 0.20, "trade": 0.10},
}
MIN_SANCTIONS_WEIGHT = 0.20

LABELS = {
    "sanctions": "制裁与合规", "litigation": "司法诉讼", "identity": "企业身份",
    "financial": "财务信用", "stability": "经营稳定性", "digital": "数字口碑",
    "trade": "贸易物流",
}
VETO_LABELS = {
    "sanctions_hit": "制裁/出口管制命中", "identity_fake": "身份无法核验或虚假",
    "bankruptcy": "破产/清算", "fraud_confirmed": "已确认欺诈信号",
}
QUICK_DIMS = ("sanctions", "identity", "digital")
MISSING_DEFAULT = 5
MISSING_WEIGHT_LIMIT = 0.40
ORDER = ["🟢 低风险", "🟡 中风险", "🔴 高风险"]


def _bump(rating, floor):
    return ORDER[max(ORDER.index(rating), ORDER.index(floor))]


def _band(score):
    if score <= 30:
        return ORDER[0]
    if score <= 60:
        return ORDER[1]
    return ORDER[2]


def validate(data):
    errs = []
    mode = data.get("mode", "deep")
    if mode not in ("deep", "quick"):
        errs.append("mode 必须是 deep 或 quick")
    scores = data.get("scores", {})
    for k in scores:
        if k not in WEIGHTS:
            errs.append(f"未知维度: {k}")
    for k, v in scores.items():
        if v is None:
            continue
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not 0 <= v <= 10:
            errs.append(f"{k} 分数必须是 0-10 的数字或 null，当前为 {v!r}")
    for k in data.get("vetoes", {}):
        if k not in VETO_LABELS:
            errs.append(f"未知否决项: {k}")
    w = data.get("weights", "default")
    if isinstance(w, str):
        if w not in PRESETS:
            errs.append(f"未知权重预设: {w}（可选 {', '.join(PRESETS)}）")
    elif isinstance(w, dict):
        if set(w) != set(WEIGHTS):
            errs.append("自定义权重必须且只能包含 7 个维度: " + ", ".join(WEIGHTS))
        elif any(not isinstance(v, (int, float)) or isinstance(v, bool) or v < 0 for v in w.values()):
            errs.append("自定义权重必须是非负数字")
        else:
            if abs(sum(w.values()) - 1) > 0.001:
                errs.append(f"自定义权重合计必须为 1，当前为 {round(sum(w.values()), 4)}")
            if w["sanctions"] < MIN_SANCTIONS_WEIGHT:
                errs.append(f"制裁与合规权重不得低于 {MIN_SANCTIONS_WEIGHT}")
    else:
        errs.append("weights 必须是预设名或字典")
    return errs


def resolve_weights(data):
    w = data.get("weights", "default")
    if isinstance(w, str):
        return PRESETS[w], w
    return {k: float(v) for k, v in w.items()}, "custom"


def score(data):
    errs = validate(data)
    if errs:
        raise ValueError("; ".join(errs))
    mode = data.get("mode", "deep")
    scores = data.get("scores", {})
    vetoes = [VETO_LABELS[k] for k, v in data.get("vetoes", {}).items() if v]
    reasons = []
    W, wsrc = resolve_weights(data)

    dims = W if mode == "deep" else {k: W[k] for k in QUICK_DIMS}
    used, missing, rows = {}, [], []
    for k in dims:
        v = scores.get(k)
        if v is None:
            missing.append(LABELS[k])
            used[k] = MISSING_DEFAULT
        else:
            used[k] = v

    if mode == "deep":
        total = round(sum(used[k] * W[k] for k in W) * 10, 1)
        rating = _band(total)
        reasons.append(f"加权总分 {total}/100 → {rating}")
        missing_w = sum(W[k] for k in W if scores.get(k) is None)
    else:
        total = None
        rating = ORDER[0]
        missing_w = sum(W[k] for k in QUICK_DIMS if scores.get(k) is None) / sum(
            W[k] for k in QUICK_DIMS)
        if any(used[k] >= 5 for k in QUICK_DIMS):
            rating = ORDER[1]
            reasons.append("快筛维度存在 ≥5 分的疑点")
        reasons.append("快筛仅给定性评级，不出 0-100 分")

    high_dims = [LABELS[k] for k in dims if scores.get(k) is not None and scores[k] >= 8]
    if high_dims:
        new = _bump(rating, ORDER[1])
        if new != rating:
            reasons.append("单维度 ≥8 分，至少中风险: " + "、".join(high_dims))
        rating = new

    low_confidence = missing_w > MISSING_WEIGHT_LIMIT
    if mode == "quick" and (scores.get("sanctions") is None or scores.get("identity") is None):
        low_confidence = True
    if low_confidence:
        new = _bump(rating, ORDER[1])
        reasons.append("信息不足，置信度低，评级至少中风险")
        rating = new

    if vetoes:
        rating = ORDER[2]
        reasons.append("一票否决: " + "、".join(vetoes))

    for k in dims:
        v = scores.get(k)
        shown = "未获取(按5计)" if v is None else v
        lvl = "🔴" if used[k] >= 8 else ("🟡" if used[k] >= 4 else "🟢")
        rows.append({"dimension": LABELS[k], "weight": f"{round(W[k]*100)}%",
                     "score": shown, "level": lvl})

    blocker = bool(data.get("trade_blocker"))
    return {
        "company": data.get("company", ""),
        "mode": mode,
        "weights": wsrc,
        "rating": rating,
        "score": total,
        "confidence": "低（信息不足）" if low_confidence else "正常",
        "vetoes": vetoes,
        "missing": missing,
        "trade_blocker": blocker,
        "trade_blocker_note": data.get("trade_blocker_note", "") if blocker else "",
        "reasons": reasons,
        "matrix": rows,
    }


def to_md(r):
    out = ["| 维度 | 权重 | 评分(0-10) | 等级 |", "|---|---|---|---|"]
    for row in r["matrix"]:
        out.append(f"| {row['dimension']} | {row['weight']} | {row['score']} | {row['level']} |")
    total = "—" if r["score"] is None else r["score"]
    out.append(f"| **总评** | | **{total}** | **{r['rating']}** |")
    out.append("")
    out.append(f"- 权重方案：{r['weights']}（自定义或非默认权重须在报告中说明理由）")
    out.append(f"- 置信度：{r['confidence']}")
    out.append(f"- 一票否决：{'、'.join(r['vetoes']) or '无'}")
    out.append(f"- 未获取：{'、'.join(r['missing']) or '无'}")
    if r["trade_blocker"]:
        out.append(f"- 品类准入：不可按现方案交易（{r['trade_blocker_note']}）")
    out.append("- 判定依据：" + "；".join(r["reasons"]))
    return "\n".join(out)


def selftest():
    full0 = {k: 0 for k in WEIGHTS}
    cases = [
        ("全部 0 分 → 低", {"scores": full0}, ORDER[0], 0.0),
        ("全部 10 分 → 高 100", {"scores": {k: 10 for k in WEIGHTS}}, ORDER[2], 100.0),
        ("全部 5 分 → 中 50", {"scores": {k: 5 for k in WEIGHTS}}, ORDER[1], 50.0),
        ("仅制裁命中分 10，其他 0 → 否决为高",
         {"scores": {**full0, "sanctions": 10}, "vetoes": {"sanctions_hit": True}}, ORDER[2], 25.0),
        ("身份 10 分但未设否决 → 单维 ≥8 至少中",
         {"scores": {**full0, "identity": 10}}, ORDER[1], 15.0),
        ("身份虚假否决 → 高",
         {"scores": {**full0, "identity": 10}, "vetoes": {"identity_fake": True}}, ORDER[2], 15.0),
        ("未获取 45% 权重 → 至少中",
         {"scores": {**full0, "financial": None, "litigation": None, "sanctions": None}}, ORDER[1], None),
        ("边界 30 分 → 低", {"scores": {k: 3 for k in WEIGHTS}}, ORDER[0], 30.0),
        ("快筛全 0 → 低", {"mode": "quick", "scores": {"sanctions": 0, "identity": 0, "digital": 0}}, ORDER[0], None),
        ("快筛缺身份 → 中", {"mode": "quick", "scores": {"sanctions": 0, "digital": 0}}, ORDER[1], None),
        ("快筛欺诈确认 → 高", {"mode": "quick", "scores": {"sanctions": 0, "identity": 0, "digital": 3},
                         "vetoes": {"fraud_confirmed": True}}, ORDER[2], None),
    ]
    fails = 0
    for name, data, want, want_score in cases:
        r = score(data)
        ok = r["rating"] == want and (want_score is None or r["score"] == want_score)
        fails += not ok
        print(("PASS " if ok else "FAIL ") + name + f"  -> {r['rating']} {r['score']}")
    for bad in ({"scores": {"sanctions": 11}}, {"scores": {"foo": 1}}, {"mode": "x"},
                {"vetoes": {"bar": True}}):
        try:
            score(bad)
            print(f"FAIL 非法输入未拦截 {bad}")
            fails += 1
        except ValueError:
            print(f"PASS 非法输入已拦截 {bad}")
    for bad in ({"weights": "nope"}, {"weights": {**WEIGHTS, "sanctions": 0.10, "digital": 0.25}},
                {"weights": {**WEIGHTS, "trade": 0.2}}, {"weights": {"sanctions": 1.0}}):
        try:
            score({"scores": full0, **bad})
            print(f"FAIL 非法权重未拦截 {bad}")
            fails += 1
        except ValueError:
            print("PASS 非法权重已拦截")
    r = score({"scores": {**full0, "stability": 10}, "weights": "project_b2b"})
    ok = r["score"] == 15.0 and r["weights"] == "project_b2b" and r["rating"] == ORDER[1]
    fails += not ok
    print(("PASS " if ok else "FAIL ") + f"预设 project_b2b 生效 -> {r['score']} {r['rating']}")
    r = score({"scores": {k: 5 for k in WEIGHTS}, "weights": "ecommerce"})
    ok = r["score"] == 50.0
    fails += not ok
    print(("PASS " if ok else "FAIL ") + "预设权重合计为 1（全 5 分 = 50）")
    r = score({"scores": full0, "trade_blocker": True, "trade_blocker_note": "加州 AB44"})
    ok = r["trade_blocker"] and r["rating"] == ORDER[0]
    fails += not ok
    print(("PASS " if ok else "FAIL ") + "trade_blocker 不改变信用评级但单独输出")
    print(f"\n{'全部通过' if not fails else f'{fails} 项失败'}")
    return fails


def main(argv):
    if "--presets" in argv:
        for name, w in PRESETS.items():
            print(name, {LABELS[k]: f"{round(v*100)}%" for k, v in w.items()})
        sys.exit(0)
    if "--selftest" in argv:
        sys.exit(1 if selftest() else 0)
    paths = [a for a in argv[1:] if not a.startswith("--")]
    if not paths:
        print(__doc__)
        sys.exit(2)
    with open(paths[0], encoding="utf-8") as f:
        data = json.load(f)
    try:
        r = score(data)
    except ValueError as e:
        print(f"输入错误: {e}", file=sys.stderr)
        sys.exit(2)
    print(to_md(r) if "--md" in argv else json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(sys.argv)
