# 制裁、出口管制与 PEP 筛查

制裁筛查步骤中阅读。快筛和深调都必须做。

## 操作步骤（每家客户都按这个顺序做）

1. **生成清单**：运行 `python3 scripts/screen_prep.py --company "<公司全称>" --person "<董事/股东/签字人>" --country <两位国家代码> --csv screening_log.csv`。脚本会输出名称变体（去掉公司后缀、处理 Al-/El- 前缀、Mohammed 等常见名的音译、西里尔字母转写、去重音），以及"每个名称 × 每个名单"的检索清单。
2. **逐项检索**：每个名单至少用前 3 个变体检索。不要只搜全称，名单里的写法常和合同上不同。
3. **集团公司分开查**：同一集团下的每个法人实体都要单独检索，不能用集团名代替。例如沙特、阿联酋的家族集团，旗下常有多家同姓公司。
4. **疑似命中先比对**：用注册号、国籍、出生日期（只用于比对，不写进报告）、地址逐项比对，能排除的写明依据，标记为"疑似已排除"。
5. **50% 规则**：受制裁方单独或合计持股达到 50% 及以上的公司，即使本身不在名单上，也按受制裁处理（见 OFAC FAQ 399：https://ofac.treasury.gov/faqs/search/399）。欧盟和英国看"所有权或控制权"，口径更宽。有 UBO 信息时，股东也要过一遍名单。
6. **留痕**：把 CSV 结果表（日期、名称、变体、名单、结果、比对说明、检查人）附在报告后面。

## 高风险国家和转运风险

- **俄罗斯、白俄罗斯**：欧盟、英国、美国的行业制裁覆盖范围很广。除了查名单，还要核对产品是否在出口禁止清单里、收货地是否在被占领地区、付款银行是否被制裁。
- **伊朗、朝鲜、古巴**：全面制裁，原则上不做。
- **叙利亚、委内瑞拉、缅甸**：制裁状态近年有调整，以签约当天的官方页面为准。
- **转运风险**：阿联酋、土耳其、中亚、高加索地区的买家，如果采购量突然放大，或者收货人与付款人不一致，要核实最终用户。必要时要求对方签最终用户声明。
- **国家风险参考**：FATF 黑名单和灰名单见 `free-paths.md` 问题 3。

## 命中之后

- **无法排除同名，或确认命中**：评分输入设 `sanctions_hit: true`（一票否决），暂停交易，交合规人员或律师判断。
- **认为名单有误**：只有被列名的当事人本人可以向 OFAC 等机构申请除名。我方能做的只是留存排除依据，不要自行"解除"命中，也不要建议对方"换个公司名再下单"。
- **已经在交易中才发现命中**：立即停止发货和收款，保留全部往来记录，咨询律师。

## 名单入口（按顺序）

1. 美国综合筛查清单 CSL：https://www.trade.gov/consolidated-screening-list —— 一次检索覆盖 OFAC SDN 等财政部名单，以及 BIS 实体清单、被拒绝人员清单、未经核实清单等商务部和国务院名单，支持模糊匹配，优先使用。网页检索需在浏览器中操作，接口需要 API 密钥；两者都不可用时，用 OpenSanctions 的 CSL 数据集代替（https://www.opensanctions.org/datasets/us_trade_csl/，覆盖实体清单、被拒绝人员清单、未经核实清单、军事最终用户清单等），并在报告中写明"CSL 经 OpenSanctions 间接检索"。
2. OFAC 单独复核（CSL 命中或疑似时）：https://sanctionssearch.ofac.treas.gov
3. 欧盟：https://www.sanctionsmap.eu（按国家看制裁制度）；实体检索用 OpenSanctions 或欧盟金融制裁综合名单 https://data.europa.eu/data/datasets/consolidated-list-of-persons-groups-and-entities-subject-to-eu-financial-sanctions
4. 联合国：https://main.un.org/securitycouncil/content/un-sc-consolidated-list
5. 英国：https://www.gov.uk/government/publications/the-uk-sanctions-list
6. 聚合与 PEP：https://www.opensanctions.org —— 聚合多国制裁名单，并收录政治公众人物（PEP）数据；免费 PEP 查询以此为主。检索地址格式 `https://www.opensanctions.org/search/?q=<名称>`，页面会显示数据更新日期，抄进报告。注意：OpenSanctions 只对非商业用途免费，企业批量使用或接入系统需购买数据许可；人工逐家检索前，请用户自行确认其使用条款。
7. 中国相关清单（中国出口商必查）：商务部不可靠实体清单与出口管制管控名单，以商务部公告为准，检索 https://www.mofcom.gov.cn 及 http://exportcontrol.mofcom.gov.cn 的最新公告。
8. 按需：世界银行禁止合作名单 https://www.worldbank.org/en/projects-operations/procurement/debarred-firms；BIS 实体清单原文 https://www.bis.gov/regulations/ear/744；瑞士 SECO https://www.sesam.search.admin.ch；香港执行联合国安理会制裁，参考 https://www.cedb.gov.hk/en/policies/united-nations-security-council-sanctions.html（香港没有独立于联合国的自主制裁名单）。

## 检索对象

公司现名、曾用名、简称；董事、股东、UBO、签字人；注册地址和收货地址；收款银行名称（如有）。

## 模糊匹配

- 法律后缀变体：Ltd / Limited / LLC / GmbH / S.A. / S.r.l. 等，检索时先去掉后缀。
- 音译变体：Mohammed / Muhammad / Mohamed；Al- / El- 前缀；西里尔字母和中日韩文名称的多种拉丁转写。
- 公司名中包含人名时，人名单独再查一次。
- 用地址反查是否有同地址的受制裁实体。

## 疑似命中的比对口径

- 疑似命中：用出生日期、国籍、注册号、地址逐项比对，写清"已排除同名"或"无法排除"。
- 无法排除或确认命中：在报告顶部发出「高风险预警」，评分输入设 `sanctions_hit: true`，建议暂停并交合规人员判断。
- 不利媒体检索：公司名/关键人名 + scam / fraud / lawsuit / sanctions / money laundering / bankruptcy，以及当地语言对应词。

## PEP 检索范围

关键人物是否担任或曾担任：国家元首、政府首脑、部长、议员、政党高层、国企高管、法官、高级检察官、高级军官、央行董事。家属和密切关系人只依据官方名录或公开报道已披露的关联，不另行搜集私人信息。

## 时效

报告中写明筛查日期。新客户签约前复查；高频客户每季度复查。
