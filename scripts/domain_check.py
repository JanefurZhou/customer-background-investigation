#!/usr/bin/env python3
"""邮箱/官网域名核验（零第三方依赖）。

判断"对方用的域名是不是声称公司的真域名"。MX 记录只能证明能收信，
骗子注册的仿冒域名通常也有 MX，所以本脚本以三项信号为主：
  1. 形似度：发件域名与官方域名是否只差 1-2 个字符或用了易混字符（rn/m、l/1、0/o）
  2. 域名年龄：RDAP 注册日期，新域名配老公司是强信号
  3. 免费邮箱：自称公司却用 Gmail/Outlook/Proton 等
另查 MX、DMARC 策略作参考。DNS 查询优先走 HTTPS（DoH），失败再走 UDP；
查不到时报告"未获取"，不会误判为"域名不存在"。

v1.5.0 起还能做三件事（都可离线）：
  4. 邮件头：--auth-results 读用户贴来的 Authentication-Results / Reply-To 行，
     判断 SPF/DKIM 是否通过、DKIM 签名域名是否就是发件域名
  5. DMARC 策略：p=none（只监控）或未设置时提示"仍可被伪造，必须看邮件头"
  6. 命名规则：--sender-name + --pattern-samples 判断发件地址是否符合公司公开邮箱的格式
     （只用来佐证，不用来推测别人的邮箱）

用法:
    python3 scripts/domain_check.py --sender sales@example-co.com --official example.com
    python3 scripts/domain_check.py --sender buyer@gmail.com --claimed-since 2005
    python3 scripts/domain_check.py --sender a@x.com --auth-results header.txt   # 邮件头判定
    python3 scripts/domain_check.py --sender jlee@x.com --sender-name "Jim Lee" \
        --pattern-samples "Ann Park:apark@x.com;Tom Hill:thill@x.com"           # 命名规则
    python3 scripts/domain_check.py --json input.json      # [{"sender": "...", "official": "...", "claimed_since": 2010}]
    python3 scripts/domain_check.py --selftest             # 离线逻辑自测
只做公开查询：不发邮件、不连业务系统、不写盘。
"""
import argparse
import datetime as dt
import json
import os
import random
import socket
import struct
import sys
import urllib.parse
import urllib.request

TIMEOUT = float(os.environ.get("DNS_TIMEOUT", "6"))
UA = {"User-Agent": "Mozilla/5.0 (due-diligence domain_check)", "accept": "application/dns-json"}
DOH = ["https://cloudflare-dns.com/dns-query", "https://dns.google/resolve"]
UDP_SERVERS = ["1.1.1.1", "8.8.8.8"]
FREEMAIL = {
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com", "msn.com",
    "yahoo.com", "ymail.com", "aol.com", "icloud.com", "me.com", "mail.com", "gmx.com",
    "gmx.de", "gmx.net", "web.de", "yandex.com", "yandex.ru", "mail.ru", "protonmail.com",
    "proton.me", "pm.me", "tutanota.com", "zoho.com", "qq.com", "163.com", "126.com",
    "sina.com", "foxmail.com", "naver.com", "hanmail.net", "libero.it", "orange.fr",
    "wanadoo.fr", "free.fr", "t-online.de", "btinternet.com", "rediffmail.com",
}
HOMOGLYPHS = [("rn", "m"), ("vv", "w"), ("cl", "d"), ("0", "o"), ("1", "l"), ("i", "l"), ("5", "s")]


# ---------- 纯逻辑（可离线自测） ----------
def domain_of(s):
    s = (s or "").strip().lower()
    if "@" in s:
        s = s.rsplit("@", 1)[1]
    for p in ("https://", "http://"):
        if s.startswith(p):
            s = s[len(p):]
    s = s.split("/")[0].split(":")[0]
    return s[4:] if s.startswith("www.") else s


def registrable(d):
    parts = d.split(".")
    two_level = {"co.uk", "org.uk", "com.au", "co.jp", "com.cn", "com.hk", "co.kr", "com.br",
                 "co.nz", "com.tr", "co.za", "com.sg", "com.my", "co.in"}
    if len(parts) >= 3 and ".".join(parts[-2:]) in two_level:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def label(d):
    return registrable(d).split(".")[0]


def levenshtein(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def skeleton(s):
    s = s.replace("-", "")
    for a, b in HOMOGLYPHS:
        s = s.replace(a, b)
    return s


def lookalike(sender, official):
    """返回 (是否形似, 说明)。完全相同或是官方子域名不算形似。"""
    if not sender or not official:
        return False, ""
    rs, ro = registrable(sender), registrable(official)
    if rs == ro:
        return False, "与官方域名一致"
    ls, lo = label(sender), label(official)
    dist = levenshtein(ls, lo)
    if ls == lo:
        return True, f"主体名相同但后缀不同（{rs} vs {ro}）"
    if skeleton(ls) == skeleton(lo):
        return True, f"使用易混字符仿冒（{rs} vs {ro}）"
    if dist <= 2 and len(lo) >= 4:
        return True, f"与官方域名只差 {dist} 个字符（{rs} vs {ro}）"
    if lo in ls and len(lo) >= 4:
        return True, f"在官方名前后加词（{rs} vs {ro}）"
    return False, f"与官方域名不同（{rs} vs {ro}），非形似"


def assess(sender_domain, official, claimed_since, facts, today=None):
    """facts: {'mx': list|None, 'dmarc': bool|None, 'created': 'YYYY-MM-DD'|None}"""
    today = today or dt.date.today()
    signals = []
    level = "🟢"

    def bump(new):
        nonlocal level
        order = ["🟢", "🟡", "🔴"]
        level = order[max(order.index(level), order.index(new))]

    is_free = registrable(sender_domain) in FREEMAIL
    if is_free:
        signals.append(("🟡", "免费/匿名邮箱：自称公司时需要求对方用公司邮箱或提供其他身份证明"))
        bump("🟡")

    look, note = lookalike(sender_domain, official) if official and not is_free else (False, "")
    if look:
        signals.append(("🔴", "形似域名：" + note + "。不要回复该地址，用官网公布的电话独立核实"))
        bump("🔴")
    elif note:
        signals.append(("ℹ️", note))

    created = facts.get("created")
    age_days = None
    if created:
        age_days = (today - dt.date.fromisoformat(created)).days
        if age_days < 180:
            signals.append(("🔴" if look else "🟡", f"域名注册仅 {age_days} 天（{created}）"))
            bump("🔴" if look else "🟡")
        if claimed_since and dt.date.fromisoformat(created).year - int(claimed_since) > 3 and age_days < 730:
            signals.append(("🟡", f"自称 {claimed_since} 年起经营，但域名 {created[:4]} 年才注册"))
            bump("🟡")
    elif not is_free:
        signals.append(("ℹ️", "域名注册日期未获取（部分国家后缀不提供 RDAP），可改用 lookup.icann.org 或当地注册局查询"))

    mx = facts.get("mx")
    if mx is None:
        signals.append(("ℹ️", "MX 未获取（网络限制），不作判断"))
    elif not mx and not is_free:
        signals.append(("ℹ️", "该域名无 MX，可能用其他域名收信；单独这一点不算风险"))
    pol = facts.get("dmarc_policy")
    if (facts.get("dmarc") is False or pol == "unset") and not is_free:
        signals.append(("ℹ️", "未设 DMARC：该域名更容易被伪造发件人，必须看原始邮件头（--auth-results）才能结案"))
    elif pol == "none" and not is_free:
        signals.append(("ℹ️", "DMARC 为 p=none（只监控不拦截）：仍可被伪造，结论最多写\"极可能来自公司邮箱\"，结案需看邮件头"))

    return {"sender_domain": sender_domain, "official_domain": official or "",
            "freemail": is_free, "lookalike": look, "created": created, "age_days": age_days,
            "mx": mx, "dmarc": facts.get("dmarc"), "dmarc_policy": pol, "level": level,
            "signals": [f"{s} {t}" for s, t in signals]}


NICK = {"jim": "james", "jimmy": "james", "bob": "robert", "rob": "robert", "bill": "william",
        "will": "william", "mike": "michael", "tom": "thomas", "dave": "david", "dan": "daniel",
        "chris": "christopher", "steve": "steven", "joe": "joseph", "tony": "anthony", "liz": "elizabeth",
        "kate": "katherine", "sam": "samuel", "alex": "alexander", "nick": "nicholas", "matt": "matthew"}


def _clean(n):
    import unicodedata
    n = unicodedata.normalize("NFKD", n or "")
    return "".join(c for c in n if c.isalpha()).lower()


def pattern_names(first, last, local):
    """返回 local（邮箱 @ 前部分）符合的命名格式列表。"""
    f, l = _clean(first), _clean(last)
    local = (local or "").lower()
    if not f or not l:
        return []
    fs = {f, NICK.get(f, f)}
    out = []
    for fn in fs:
        cand = {
            "first.last": f"{fn}.{l}", "firstlast": f"{fn}{l}", "first_last": f"{fn}_{l}",
            "flast": f"{fn[0]}{l}", "f.last": f"{fn[0]}.{l}", "first": fn, "last": l,
            "lastf": f"{l}{fn[0]}", "last.first": f"{l}.{fn}", "firstl": f"{fn}{l[0]}", "first.l": f"{fn}.{l[0]}",
        }
        out += [k for k, v in cand.items() if v == local and k not in out]
    return out


def pattern_check(sender, sender_name, samples):
    """samples: [(姓名, 邮箱), ...]；返回 (符号, 说明, 主流格式)。"""
    from collections import Counter
    cnt = Counter()
    for name, mail in samples:
        parts = (name or "").split()
        if len(parts) < 2 or "@" not in mail:
            continue
        for p in pattern_names(parts[0], parts[-1], mail.split("@")[0]):
            cnt[p] += 1
    if not cnt:
        return "ℹ️", "命名规则未获取：样本不足或无法识别格式", None
    top, n = cnt.most_common(1)[0]
    parts = (sender_name or "").split()
    if len(parts) < 2:
        return "ℹ️", f"公司公开邮箱主要格式为 {top}（{n} 个样本）；未提供发件人姓名，无法比对", top
    mine = pattern_names(parts[0], parts[-1], sender.split("@")[0])
    if top in mine:
        return "✅", f"发件地址符合公司公开邮箱格式 {top}（{n} 个样本），佐证为内部账号", top
    return "ℹ️", f"发件地址不符合公司公开邮箱格式 {top}（{n} 个样本）；只记录，不单独判风险", top


def parse_auth_results(text, sender_domain):
    """解析用户贴来的原始邮件头片段，返回 {spf, dkim, dmarc, dkim_domain, reply_to, level, signals}。"""
    import re
    low = (text or "").lower()
    def res(key):
        m = re.search(key + r"\s*=\s*([a-z]+)", low)
        return m.group(1) if m else None
    spf, dkim, dmarc = res(r"\bspf"), res(r"\bdkim"), res(r"\bdmarc")
    m = re.search(r"header\.(?:d|i)\s*=\s*@?([a-z0-9.-]+)", low)
    dkim_domain = m.group(1) if m else None
    m = re.search(r"^reply-to:.*?([a-z0-9._%+-]+@[a-z0-9.-]+)", low, re.M)
    reply_to = m.group(1) if m else None
    sd = registrable(domain_of(sender_domain))
    aligned = bool(dkim_domain) and registrable(dkim_domain) == sd
    signals, level = [], "🟡"
    if dmarc == "pass" or (dkim == "pass" and aligned):
        level = "🟢"
        signals.append("✅ 邮件头通过：" + ("DMARC=pass" if dmarc == "pass" else f"DKIM=pass 且签名域名 {dkim_domain} 与发件域名一致") + "，发件真实性可以结案")
    elif spf == "fail" and dkim in ("fail", None) or dmarc == "fail":
        level = "🔴"
        signals.append(f"🔴 邮件头未通过（SPF={spf}, DKIM={dkim}, DMARC={dmarc}）：冒充信号，用官方总机回拨核实")
    elif dkim == "pass" and not aligned:
        signals.append(f"🟡 DKIM 通过但签名域名 {dkim_domain} 不是发件域名 {sd}：可能是代发平台，需进一步核实")
    elif spf == "pass":
        signals.append("🟡 只有 SPF 通过、没有对齐的 DKIM：可信度一般，结合回拨判断")
    else:
        signals.append("ℹ️ 邮件头里没找到可判断的 SPF/DKIM/DMARC 结果，请贴完整的 Authentication-Results 行")
    if reply_to and registrable(domain_of(reply_to)) != sd:
        level = "🔴" if level != "🟢" else "🟡"
        signals.append(f"🔴 Reply-To 指向其他域名（{reply_to}）：回复会被转走，典型冒充手法")
    return {"spf": spf, "dkim": dkim, "dmarc": dmarc, "dkim_domain": dkim_domain,
            "reply_to": reply_to, "aligned": aligned, "level": level, "signals": signals}


# ---------- 网络查询 ----------
def _http_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))


def _doh(name, rtype):
    for base in DOH:
        try:
            d = _http_json(f"{base}?name={urllib.parse.quote(name)}&type={rtype}")
            if d.get("Status") == 3:      # NXDOMAIN
                return []
            if d.get("Status") == 0:
                return [a["data"] for a in d.get("Answer", []) if a.get("type") in (15, 16)]
        except Exception:
            continue
    return None


def _udp_mx(domain):
    for server in UDP_SERVERS:
        try:
            tid = random.randint(0, 0xFFFF)
            q = struct.pack(">HHHHHH", tid, 0x0100, 1, 0, 0, 0)
            for part in domain.split("."):
                q += bytes([len(part)]) + part.encode("ascii", "ignore")
            q += b"\x00" + struct.pack(">HH", 15, 1)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(TIMEOUT)
            s.sendto(q, (server, 53))
            data, _ = s.recvfrom(4096)
            s.close()
            rid, flags, _, an, _, _ = struct.unpack(">HHHHHH", data[:12])
            rcode = flags & 0x000F
            if rid != tid or not (flags & 0x8000):
                continue
            if rcode == 3:
                return []
            if rcode != 0:
                continue                   # REFUSED/SERVFAIL：视为未获取
            return ["(udp) %d answers" % an] if an else []
        except Exception:
            continue
    return None


def mx_records(domain):
    r = _doh(domain, "MX")
    return r if r is not None else _udp_mx(domain)


def dmarc_info(domain):
    """返回 (是否设置 DMARC, 策略 none/quarantine/reject/unset/None)。None 表示未获取。"""
    import re
    r = _doh("_dmarc." + domain, "TXT")
    if r is None:
        return None, None
    recs = [x for x in r if "v=dmarc1" in x.lower()]
    if not recs:
        return False, "unset"
    m = re.search(r"\bp\s*=\s*(none|quarantine|reject)", recs[0].lower())
    return True, (m.group(1) if m else "none")


def has_dmarc(domain):
    return dmarc_info(domain)[0]


def rdap_created(domain):
    try:
        d = _http_json("https://rdap.org/domain/" + registrable(domain))
        for e in d.get("events", []):
            if e.get("eventAction") == "registration":
                return e["eventDate"][:10]
    except Exception:
        return None
    return None


def check(sender, official=None, claimed_since=None):
    sd = domain_of(sender)
    od = domain_of(official) if official else ""
    if registrable(sd) in FREEMAIL:
        facts = {"mx": ["(免费邮箱服务)"], "dmarc": None, "created": None}
    else:
        dm, pol = dmarc_info(sd)
        facts = {"mx": mx_records(sd), "dmarc": dm, "dmarc_policy": pol, "created": rdap_created(sd)}
    r = assess(sd, od, claimed_since, facts)
    if od and registrable(od) != registrable(sd):
        oc = rdap_created(od)
        r["official_created"] = oc
        if oc and r["created"] and r["created"] > oc:
            r["signals"].append(f"ℹ️ 官方域名注册于 {oc}，发件域名注册于 {r['created']}（晚 {int(r['created'][:4]) - int(oc[:4])} 年）")
    return r


# ---------- 自测 ----------
def selftest():
    T = dt.date(2026, 10, 19)
    cases = [
        ("形似域名+新注册 → 红", assess("optiklasers.com", "optilasers.com", None,
                                     {"mx": ["mail.optiklasers.com"], "dmarc": False, "created": "2026-03-04"}, T), "🔴"),
        ("官方域名本身 → 绿", assess("optilasers.com", "optilasers.com", None,
                                 {"mx": ["mail.optilasers.com"], "dmarc": True, "created": "1998-02-23"}, T), "🟢"),
        ("易混字符 rn/m → 红", assess("rnodaco.com", "modaco.com", None, {"mx": ["x"], "dmarc": True, "created": "2020-01-01"}, T), "🔴"),
        ("后缀不同 → 红", assess("brandx.co", "brandx.com", None, {"mx": ["x"], "dmarc": True, "created": "2015-01-01"}, T), "🔴"),
        ("免费邮箱 → 黄", assess("gmail.com", "brandx.com", None, {"mx": ["x"], "dmarc": None, "created": None}, T), "🟡"),
        ("老域名无 MX → 绿（不判风险）", assess("oldbrand.com", "", None, {"mx": [], "dmarc": False, "created": "2000-03-06"}, T), "🟢"),
        ("DNS 未获取 → 不误判", assess("brandx.com", "brandx.com", None, {"mx": None, "dmarc": None, "created": None}, T), "🟢"),
        ("自称 2005 年但域名 2026 年 → 黄", assess("newco.com", "", 2005, {"mx": ["x"], "dmarc": True, "created": "2026-01-10"}, T), "🟡"),
        ("官方子域名 → 绿", assess("mail.brandx.com", "brandx.com", None, {"mx": ["x"], "dmarc": True, "created": "2010-01-01"}, T), "🟢"),
        ("无关域名 → 不判形似", assess("othercorp.com", "brandx.com", None, {"mx": ["x"], "dmarc": True, "created": "2010-01-01"}, T), "🟢"),
    ]
    fails = 0
    for name, r, want in cases:
        ok = r["level"] == want
        fails += not ok
        print(("PASS " if ok else "FAIL ") + f"{name} -> {r['level']}")
    r = assess("brandx.com", "brandx.com", None, {"mx": ["x"], "dmarc": True, "dmarc_policy": "none", "created": "2001-01-01"}, T)
    extra = [
        ("DMARC p=none → 提示看邮件头", any("p=none" in s for s in r["signals"]) and r["level"] == "🟢"),
    ]
    good = "Authentication-Results: mx.example; spf=pass smtp.mailfrom=brandx.com; dkim=pass header.d=brandx.com; dmarc=pass"
    extra.append(("邮件头全部通过 → 可结案", parse_auth_results(good, "a@brandx.com")["level"] == "🟢"))
    bad = "Authentication-Results: mx; spf=fail smtp.mailfrom=brandx.com; dkim=fail header.d=brandx.com"
    extra.append(("SPF+DKIM 都 fail → 红", parse_auth_results(bad, "a@brandx.com")["level"] == "🔴"))
    rt = good + "\nReply-To: Pay Dept <billing@brandx-pay.com>"
    extra.append(("Reply-To 指向别的域名 → 降级并报警", any("Reply-To" in s for s in parse_auth_results(rt, "a@brandx.com")["signals"])
                  and parse_auth_results(rt, "a@brandx.com")["level"] != "🟢"))
    na = "Authentication-Results: mx; spf=pass; dkim=pass header.d=mailer-platform.com"
    extra.append(("DKIM 签名域名不一致 → 黄", parse_auth_results(na, "a@brandx.com")["level"] == "🟡"))
    smp = [("Ann Park", "apark@brandx.com"), ("Tom Hill", "thill@brandx.com"), ("Lea Wong", "lwong@brandx.com")]
    extra.append(("命名规则吻合（Jim 视同 James）", pattern_check("jlee@brandx.com", "Jim Lee", smp)[0] == "✅"))
    extra.append(("命名规则不符 → 只记录", pattern_check("jim.lee@brandx.com", "Jim Lee", smp)[0] == "ℹ️"))
    extra.append(("样本不足 → 未获取", pattern_check("x@brandx.com", "Jim Lee", [])[2] is None))
    for name, ok in extra:
        fails += not ok
        print(("PASS " if ok else "FAIL ") + name)
    print("\n全部通过" if not fails else f"\n{fails} 项失败")
    return fails


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sender", help="对方邮箱或域名")
    ap.add_argument("--official", help="声称公司的官方域名（从官网或登记信息确认）")
    ap.add_argument("--claimed-since", type=int, help="对方自称的成立年份")
    ap.add_argument("--json", help="批量输入 JSON 文件")
    ap.add_argument("--auth-results", help="原始邮件头片段文件（Authentication-Results、Reply-To 行）")
    ap.add_argument("--sender-name", help="发件人姓名，用于命名规则比对")
    ap.add_argument("--pattern-samples", help="公司公开邮箱样本：\"姓名:邮箱;姓名:邮箱\"")
    ap.add_argument("--offline", action="store_true", help="不做 DNS/RDAP 查询，只跑邮件头和命名规则")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(1 if selftest() else 0)
    if a.json:
        with open(a.json, encoding="utf-8") as f:
            items = json.load(f)
        out = [check(i.get("sender", ""), i.get("official"), i.get("claimed_since")) for i in items]
    elif a.sender:
        out = {"sender_domain": domain_of(a.sender)} if a.offline else check(a.sender, a.official, a.claimed_since)
        if a.auth_results:
            with open(a.auth_results, encoding="utf-8", errors="ignore") as f:
                out["auth_results"] = parse_auth_results(f.read(), a.sender)
        if a.pattern_samples:
            smp = []
            for item in a.pattern_samples.split(";"):
                if ":" in item:
                    n, m = item.split(":", 1)
                    smp.append((n.strip(), m.strip()))
            sym, note, top = pattern_check(a.sender, a.sender_name, smp)
            out["naming_pattern"] = {"result": sym, "pattern": top, "note": note}
    else:
        ap.print_help()
        sys.exit(2)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
