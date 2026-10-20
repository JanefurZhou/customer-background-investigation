#!/usr/bin/env python3
"""制裁筛查准备：生成名称变体、检索链接和结果记录表（零第三方依赖）。

解决两个问题：
  1. 阿拉伯语、西里尔字母等名称的音译差异，以及公司后缀不同造成的漏检
  2. 多个名单、多个名称逐个检索时容易漏项，结果没有留痕

用法:
    python3 scripts/screen_prep.py --company "Al-Rashid Trading Co. LLC" --person "Mohammed Al Rashid" --country SA
    python3 scripts/screen_prep.py --company "ООО Ромашка" --csv screening_log.csv
    python3 scripts/screen_prep.py --selftest
输出：Markdown 检索清单（每个名称 × 每个名单），可选 CSV 记录表（填写结果后存档）。
本脚本只生成清单，不代替实际检索；结果以官方名单页面为准。
"""
import argparse
import csv
import datetime as dt
import re
import sys
import unicodedata
import urllib.parse

LEGAL_SUFFIXES = [
    "limited liability company", "public limited company", "joint stock company", "private limited",
    "company limited", "pvt ltd", "co ltd", "pte ltd", "sdn bhd", "sp z oo", "fz llc", "l l c",
    "limited", "ltd", "llc", "inc", "incorporated", "corp", "corporation", "plc", "gmbh", "ag", "kg",
    "sa", "sas", "srl", "spa", "bv", "nv", "oy", "ab", "as", "a/s", "ooo", "oao", "zao", "pao",
    "jsc", "ojsc", "cjsc", "bhd", "pt", "tbk", "fze", "fzco", "wll", "lp", "llp",
    "cong ty", "tnhh", "co phan", "cổ phần",
]
DESCRIPTIVE = ["trading", "group", "holding", "holdings", "company", "co", "establishment", "est",
               "international", "intl", "import export", "imp exp", "enterprises", "industries"]
CYRILLIC = dict(zip(
    "абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
    ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "y", "k", "l", "m", "n", "o", "p", "r", "s",
     "t", "u", "f", "kh", "ts", "ch", "sh", "shch", "", "y", "", "e", "yu", "ya"]))
CYR_ALT = {"kh": "h", "y": "j", "yu": "iu", "ya": "ia", "zh": "j", "ts": "c"}
ARABIC_GIVEN = [
    {"mohammed", "muhammad", "mohamed", "mohammad", "muhammed", "mohamad", "mohd"},
    {"ahmed", "ahmad"}, {"abdullah", "abdallah", "abdulla"}, {"abdulaziz", "abdul aziz", "abd al aziz", "abdelaziz"},
    {"abdulrahman", "abdul rahman", "abdelrahman", "abd al rahman", "abdurrahman"},
    {"hussein", "husain", "hussain", "husayn", "hosein"}, {"hassan", "hasan"},
    {"khaled", "khalid"}, {"omar", "umar"}, {"youssef", "yousef", "yusuf", "yousuf"},
    {"saleh", "salih", "salah"}, {"faisal", "faysal", "feisal"},
]
SANCTIONS_LISTS = [
    ("美国 CSL（含 OFAC SDN、BIS 等）", "https://www.trade.gov/consolidated-screening-list", None),
    ("OFAC Sanctions List Search", "https://sanctionssearch.ofac.treas.gov", None),
    ("OpenSanctions（EU/UN/UK/PEP 等聚合）", "https://www.opensanctions.org/search/?q={q}", "url"),
    ("UK Sanctions List", "https://www.gov.uk/government/publications/the-uk-sanctions-list", None),
    ("UN 安理会综合名单", "https://main.un.org/securitycouncil/content/un-sc-consolidated-list", None),
    ("中国商务部不可靠实体清单 / 出口管制管控名单", "https://www.mofcom.gov.cn", None),
    ("不利媒体（搜索引擎）", "https://www.google.com/search?q=%22{q}%22+(sanctions+OR+fraud+OR+scam+OR+lawsuit+OR+bankruptcy)", "url"),
]
HIGH_RISK_HINT = {
    "RU": "俄罗斯：EU/UK/US 行业制裁广泛，必须查 50% 规则（受制裁方合计持股 ≥50% 的实体同样受限）和收货地是否在被占领地区",
    "BY": "白俄罗斯：同俄罗斯，行业制裁 + 50% 规则",
    "IR": "伊朗：美国全面制裁，原则上不做",
    "KP": "朝鲜：全面制裁，不做",
    "SY": "叙利亚：制裁状态近年有调整，以签约当天的官方名单和政策为准",
    "CU": "古巴：美国全面禁运，涉美元结算或美国成分时不做",
    "VE": "委内瑞拉：美国对政府及国企的制裁，核查是否为国企或其关联方",
    "MM": "缅甸：针对军方关联企业的定向制裁",
    "AE": "阿联酋：转口贸易枢纽，留意最终收货人是否在受制裁国家（转运风险）",
    "TR": "土耳其：转口风险，同上",
    "KZ": "哈萨克斯坦等中亚国家：对俄转运风险，核实最终用户",
    "KG": "吉尔吉斯斯坦：对俄转运风险，核实最终用户",
    "AM": "亚美尼亚：对俄转运风险，核实最终用户",
}


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip()


def translit_cyr(s):
    out = []
    for ch in s:
        low = ch.lower()
        if low in CYRILLIC:
            t = CYRILLIC[low]
            out.append(t.capitalize() if ch.isupper() and t else t)
        else:
            out.append(ch)
    return "".join(out)


def _clean(name):
    n = re.sub(r"\b([a-z])\.(?=[a-z]\b)", r"\1", name.lower())   # s.r.l. -> srl.
    n = re.sub(r"\b([a-z]{1,3})\.(?=\s|$|,)", r"\1", n)          # co. / srl. -> co / srl
    n = n.replace(",", " ").replace("&", " and ").replace(".", " ")
    n = re.sub(r"[\"'“”«»()]", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def _strip(n, words):
    changed = True
    while changed:
        changed = False
        for suf in sorted(words, key=len, reverse=True):
            for pat in (r"(^|\s)" + re.escape(suf) + r"$", r"^" + re.escape(suf) + r"(\s|$)"):
                new = re.sub(pat, " ", n).strip()
                if new != n and new:
                    n, changed = new, True
    return n


def strip_suffixes(name, descriptive=False):
    n = _strip(_clean(name), LEGAL_SUFFIXES)
    return _strip(n, LEGAL_SUFFIXES + DESCRIPTIVE) if descriptive else n


def arabic_variants(name):
    n = name.lower()
    vs = {n}
    # Al-/El-/Al /去前缀
    for v in list(vs):
        vs.add(re.sub(r"\b(al|el)[- ]", "al-", v))
        vs.add(re.sub(r"\b(al|el)[- ]", "al ", v))
        vs.add(re.sub(r"\b(al|el)[- ]", "el-", v))
        vs.add(re.sub(r"\b(al|el)[- ]", "", v))
        vs.add(re.sub(r"\b(al|el)-", "al", v))
    for group in ARABIC_GIVEN:
        for v in list(vs):
            for g in group:
                if re.search(r"\b" + re.escape(g) + r"\b", v):
                    for alt in group:
                        vs.add(re.sub(r"\b" + re.escape(g) + r"\b", alt, v))
    vs.update({v.replace("bin ", "ibn ") for v in list(vs)} | {v.replace("ibn ", "bin ") for v in list(vs)})
    return vs


def variants(name):
    base = norm(name)
    out = [base]
    if re.search(r"[\u0400-\u04FF]", base):
        lat = translit_cyr(base)
        out.append(lat)
        alt = lat.lower()
        for a, b in CYR_ALT.items():
            alt = alt.replace(a, b)
        out.append(alt)
    src = out[-1] if len(out) > 1 else base
    core = strip_suffixes(src)
    core2 = strip_suffixes(src, descriptive=True)
    out.append(core)
    if core2 != core:
        out.append(core2)
    out.extend(sorted(arabic_variants(core2)))
    seen, res = set(), []
    for v in out:
        k = re.sub(r"\s+", " ", v.lower()).strip(" -")
        if k and k not in seen and len(k) >= 2:
            seen.add(k)
            res.append(v.strip(" -"))
    return res[:25]


def build(company=None, persons=(), country=None, address=None):
    today = dt.date.today().isoformat()
    targets = []
    if company:
        targets.append(("公司", company, variants(company)))
    for p in persons:
        targets.append(("人员", p, variants(p)))
    if address:
        targets.append(("地址", address, [norm(address)]))
    md = [f"# 制裁筛查清单（生成日期 {today}）", ""]
    if country and country.upper() in HIGH_RISK_HINT:
        md += [f"> ⚠️ {HIGH_RISK_HINT[country.upper()]}", ""]
    md += ["检索规则：每个名单至少用前 3 个变体检索；疑似命中时用出生日期、国籍、注册号、地址逐项比对，记录排除依据。",
           "集团公司：同一集团下的每个法人实体单独检索，不能用集团名代替。", ""]
    rows = []
    for kind, raw, vs in targets:
        md.append(f"## {kind}：{raw}")
        md.append("变体：" + " ｜ ".join(vs))
        md.append("")
        md.append("| 名单 | 检索 | 结果 |")
        md.append("|---|---|---|")
        for lname, url, mode in SANCTIONS_LISTS:
            q = vs[min(2, len(vs) - 1)] if kind != "地址" else vs[0]
            link = url.format(q=urllib.parse.quote(q)) if mode == "url" else url
            md.append(f"| {lname} | [{q}]({link}) | ☐ 未命中 ☐ 疑似已排除 ☐ 命中 |")
            rows.append({"date": today, "type": kind, "query_name": raw, "variants_used": " | ".join(vs[:3]),
                         "list": lname, "url": link, "result": "", "match_note": "", "checked_by": ""})
        md.append("")
    md += ["## 命中后怎么办",
           "1. 先排除同名：比对出生日期、国籍、注册号、地址；能排除的写明依据，记为“疑似已排除”。",
           "2. 无法排除：评分输入设 sanctions_hit: true（一票否决），暂停交易，交给合规人员或律师判断。",
           "3. 50% 规则：受制裁方单独或合计持股 ≥50% 的公司，即使本身不在名单上，也按受制裁处理（OFAC FAQ 399）。",
           "4. 认为名单有误：只有被列名的当事人本人可以向 OFAC 等机构申请除名；我方能做的只是留存排除依据，不要自行“解除”命中。",
           "5. 留痕：把本清单和 CSV 结果表附在报告后面，签约前复查。"]
    return "\n".join(md), rows


def selftest():
    fails = 0
    def check(name, cond):
        nonlocal fails
        fails += not cond
        print(("PASS " if cond else "FAIL ") + name)
    v = [x.lower() for x in variants("Al-Rashid Trading Co. LLC")]
    check("去公司后缀", "rashid" in v or "al-rashid" in v or "al rashid" in v)
    check("Al-/El- 变体", any(x.startswith("el-") for x in v) and any(x == "rashid" for x in v))
    p = [x.lower() for x in variants("Mohammed Al Rashid")]
    check("Mohammed 音译变体", any("muhammad" in x for x in p) and any("mohamed" in x for x in p))
    c = [x.lower() for x in variants("ООО Ромашка")]
    check("西里尔转写 + 去 OOO", "romashka" in c)
    g = [x.lower() for x in variants("Müller GmbH")]
    check("去重音 + 去 GmbH", "muller" in g)
    md, rows = build("Example Trading LLC", ["Ahmed Hassan"], "RU")
    check("高风险国家提示", "50%" in md)
    check("每个名称 × 每个名单都生成一行", len(rows) == 2 * len(SANCTIONS_LISTS))
    check("S.R.L. 点号后缀", "rossi" in [x.lower() for x in variants("S.R.L. Rossi")])
    check("越南 JSC", "minh an" in [x.lower() for x in variants("Minh An Joint Stock Company")])
    check("变体数量有上限", len(variants("Mohammed Abdulrahman Al Hussein bin Khalid")) <= 25)
    print("\n全部通过" if not fails else f"\n{fails} 项失败")
    return fails


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--company")
    ap.add_argument("--person", action="append", default=[], help="可重复：董事、股东、签字人、联系人")
    ap.add_argument("--country", help="ISO 两位国家代码，如 SA、RU、AE")
    ap.add_argument("--address")
    ap.add_argument("--csv", help="同时输出结果记录表 CSV")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(1 if selftest() else 0)
    if not (a.company or a.person):
        ap.print_help()
        sys.exit(2)
    md, rows = build(a.company, a.person, a.country, a.address)
    print(md)
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"\n结果记录表已写入 {a.csv}", file=sys.stderr)


if __name__ == "__main__":
    main()
