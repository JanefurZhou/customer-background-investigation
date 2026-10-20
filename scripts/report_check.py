#!/usr/bin/env python3
"""背调报告交付前自检（纯标准库）。

用法：
  python3 scripts/report_check.py DD_<简称>_<YYYYMMDD>.md [--mode quick|deep]
  python3 scripts/report_check.py --selftest

检查项（任一 FAIL 即不交付，退出码 1）：
  1 来源      至少 3 个 http(s) 来源链接（深调至少 6 个）
  2 占位符    没有残留的模板占位符（[填写]、YYYY-MM-DD、X/100、空的 level = 等）
  3 未获取    写明了未获取项；查不到的写"暂未检索到公开信源"或"未获取"
  4 制裁筛查  写明筛查日期，并保留筛查结果表（screening_log.csv）
  5 评级付款  评级为 🟢/🟡/🔴 之一，并给出付款方式建议
  6 台账      写明已用 dd_ledger.py 记录，回写字段 dd_rating 已填写
  7 询盘核验  企业主体："发件人"和"签约主体"两行已填写（个人买家跳过）
  8 建议动作  有"建议动作"一节，且至少一条
深调另查：风险分为 0–100 的数字。

脚本只能检查格式和留痕。"没有编造人名、网址、电话"这一项必须由人工逐条核对来源。
"""
import re
import sys

PLACEHOLDERS = [
    (r"\[填写", "[填写…]"),
    (r"YYYY-MM-DD", "YYYY-MM-DD"),
    (r"X/100", "X/100"),
    (r"\[1[–-]2 句", "[1–2 句…]"),
    (r"\[公司全称", "[公司全称…]"),
    (r"level = ，", "空的 level ="),
    (r"🟢 / 🟡 / 🔴", "未选定的评级"),
    (r"🟢/🟡/🔴", "未选定的评级"),
    (r"✅存续 / ⚠️异常 / ❌未查到", "未选定的登记状态"),
    (r"\[姓名", "[姓名…]"),
    (r"\[法定实体", "[法定实体…]"),
    (r"\[动作", "[动作…]"),
]
PAY_WORDS = ["定金", "T/T", "信用证", "正常合作", "暂停", "账期", "出口信用保险"]


def detect_mode(text):
    return "deep" if ("深度尽调报告" in text or "模式：深度尽调" in text) else "quick"


def check(text, mode=None):
    mode = mode or detect_mode(text)
    res = []
    urls = set(re.findall(r"https?://[^\s)\]|>，。]+", text))
    need = 6 if mode == "deep" else 3
    res.append(("来源", len(urls) >= need, f"{len(urls)} 个来源链接（至少 {need} 个）"))
    left = [label for pat, label in PLACEHOLDERS if re.search(pat, text)]
    res.append(("占位符", not left, "无残留" if not left else "残留：" + "、".join(left)))
    has_missing = bool(re.search(r"未获取[：:]|未获取清单[：:]|暂未检索到公开信源", text))
    res.append(("未获取", has_missing, "已写明" if has_missing else "缺少未获取清单"))
    date_ok = bool(re.search(r"筛查日期[^\n]{0,6}\d{4}-\d{2}-\d{2}", text))
    log_ok = ("screening_log" in text) or ("筛查结果表" in text)
    res.append(("制裁筛查", date_ok and log_ok,
                ("日期" + ("✓" if date_ok else "✗")) + " / " + ("留痕" + ("✓" if log_ok else "✗"))))
    rating = re.search(r"评级[^\n]{0,8}(🟢|🟡|🔴)", text)
    pay = any(w in text for w in PAY_WORDS)
    res.append(("评级付款", bool(rating) and pay,
                ("评级" + ("✓" if rating else "✗")) + " / " + ("付款建议" + ("✓" if pay else "✗"))))
    ledger = "dd_ledger" in text
    filled = bool(re.search(r"dd_rating=(green|yellow|red|🟢|🟡|🔴)", text))
    res.append(("台账", ledger and filled,
                ("台账" + ("✓" if ledger else "✗")) + " / " + ("dd_rating" + ("✓" if filled else "✗"))))
    personal = bool(re.search(r"主体类型[^\n]{0,6}个人买家", text))
    if personal:
        res.append(("询盘核验", True, "个人买家，跳过"))
    else:
        def filled(label):
            m = re.search(label + r"[^\n|]*[|：:]\s*([^\n|]+)", text)
            return bool(m) and m.group(1).strip() not in ("", "-", "—")
        snd, ent = filled("发件人"), filled("签约主体")
        res.append(("询盘核验", snd and ent,
                    ("发件人" + ("✓" if snd else "✗")) + " / " + ("签约主体" + ("✓" if ent else "✗"))))
    m = re.search(r"#+\s*建议动作[^\n]*\n(.*?)(?=\n#+\s|\Z)", text, re.S)
    acts = len(re.findall(r"^\s*(?:\d+[.、]|[-*]|\|\s*\d)", m.group(1), re.M)) if m else 0
    res.append(("建议动作", acts >= 1, f"{acts} 条" if m else "缺少\"建议动作\"一节"))
    if mode == "deep":
        sc = re.search(r"风险分[：:]\s*(\d{1,3})\s*/\s*100", text)
        ok = bool(sc) and 0 <= int(sc.group(1)) <= 100
        res.append(("风险分", ok, sc.group(0) if sc else "未写数字风险分"))
    return mode, res


def report(path, mode=None):
    text = open(path, encoding="utf-8").read()
    mode, res = check(text, mode)
    print(f"# 交付自检：{path}（{'深调' if mode == 'deep' else '快筛'}）")
    for name, ok, detail in res:
        print(f"{'PASS' if ok else 'FAIL'}  {name}：{detail}")
    print("人工必查：报告里的人名、网址、电话、注册号都能在所附来源中找到，没有编造。")
    bad = [n for n, ok, _ in res if not ok]
    print("结论：" + ("可以交付" if not bad else "不予交付，先补齐：" + "、".join(bad)))
    return 0 if not bad else 1


GOOD_QUICK = """# 客户快速筛查简报：Demo Trading Ltd
| 评级 | 🟢 低风险 |
## 结论
可以报价，按 30% 定金 + 70% 见提单副本。
## 身份核验
- 登记状态：✅存续（https://find-and-update.company-information.service.gov.uk/company/00000000）
## 询盘核验
- 发件人：Ann Park，采购经理，官网团队页可见
- 签约主体：Demo Trading Ltd（与对外品牌一致）
## 制裁与出口管制（筛查日期 2026-10-19）
- CSL 未命中 https://www.trade.gov/consolidated-screening-list
- OpenSanctions 未命中 https://www.opensanctions.org/
## 风险信号与未获取项
- 未获取：财务报表（暂未检索到公开信源）
## 留痕
- 制裁筛查结果表：screening_log.csv
- 台账：已用 dd_ledger.py add 记录
## 建议动作
1. 回拨官网总机确认 Ann Park 在职（5 分钟）
## 回写字段
dd_mode=quick, dd_rating=green
"""


def selftest():
    cases = []
    m, r = check(GOOD_QUICK)
    cases.append(("完整快筛通过", m == "quick" and all(ok for _, ok, _ in r)))
    _, r = check(GOOD_QUICK.replace("https://www.opensanctions.org/", ""))
    cases.append(("来源不足 → FAIL", not dict((n, ok) for n, ok, _ in r)["来源"]))
    _, r = check(GOOD_QUICK + "\n筛查日期 YYYY-MM-DD")
    cases.append(("残留占位符 → FAIL", not dict((n, ok) for n, ok, _ in r)["占位符"]))
    _, r = check(GOOD_QUICK.replace("- 未获取：财务报表（暂未检索到公开信源）", "- 无"))
    cases.append(("缺未获取清单 → FAIL", not dict((n, ok) for n, ok, _ in r)["未获取"]))
    _, r = check(GOOD_QUICK.replace("- 制裁筛查结果表：screening_log.csv\n", ""))
    cases.append(("缺筛查留痕 → FAIL", not dict((n, ok) for n, ok, _ in r)["制裁筛查"]))
    _, r = check(GOOD_QUICK.replace("dd_rating=green", "dd_rating="))
    cases.append(("dd_rating 未填 → FAIL", not dict((n, ok) for n, ok, _ in r)["台账"]))
    deep = "# 客户背景调查报告：Demo\n- 模式：深度尽调\n- 评级：🟡 | 风险分：42/100\n" + GOOD_QUICK + \
        "\nhttps://a.example/1 https://a.example/2 https://a.example/3"
    m, r = check(deep)
    cases.append(("完整深调通过", m == "deep" and all(ok for _, ok, _ in r)))
    m, r = check(deep.replace("风险分：42/100", "风险分：待定"))
    cases.append(("深调缺风险分 → FAIL", not dict((n, ok) for n, ok, _ in r)["风险分"]))
    _, r = check(GOOD_QUICK.replace("- 签约主体：Demo Trading Ltd（与对外品牌一致）\n", ""))
    cases.append(("企业缺签约主体 → FAIL", not dict((n, ok) for n, ok, _ in r)["询盘核验"]))
    _, r = check(GOOD_QUICK.replace("- 发件人：Ann Park，采购经理，官网团队页可见\n", "").replace(
        "- 签约主体：Demo Trading Ltd（与对外品牌一致）\n", "") + "\n| 主体类型 | 个人买家 |")
    cases.append(("个人买家跳过询盘核验", dict((n, ok) for n, ok, _ in r)["询盘核验"]))
    _, r = check(GOOD_QUICK.replace("## 建议动作\n1. 回拨官网总机确认 Ann Park 在职（5 分钟）\n", ""))
    cases.append(("缺建议动作 → FAIL", not dict((n, ok) for n, ok, _ in r)["建议动作"]))
    fails = 0
    for name, ok in cases:
        print(("PASS " if ok else "FAIL ") + name)
        fails += 0 if ok else 1
    print("全部通过" if not fails else f"{fails} 项失败")
    return 0 if not fails else 1


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)
    if a[0] == "--selftest":
        sys.exit(selftest())
    mode = None
    if "--mode" in a:
        i = a.index("--mode")
        mode = a[i + 1]
        del a[i:i + 2]
    sys.exit(report(a[0], mode))
