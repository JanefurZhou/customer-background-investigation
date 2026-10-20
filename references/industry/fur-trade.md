# 行业插件：皮草、仿皮草与动物纤维

当交易涉及真皮草、动物毛皮装饰、羊毛或羊绒，或对方自称做仿皮草时阅读。本文件补充两件事：一是这个品类在目的地能不能卖（`trade_blocker`），二是行业专属的身份核验点。通用流程保持不变。法规会变，下结论前先打开官方页面确认现行状态，并在报告里写明核验日期。

## 1. 先判断三件事

1. 产品是真皮草、仿皮草，还是混合（比如仿皮草主体搭配真毛领）？物种名称是什么？
2. 最终在哪里销售？看的是最终销售地，而不只是收货地。例如美国客户如果在加州有门店，就适用加州的规定。
3. 对方是否公开承诺 fur-free？有这类承诺的品牌只能推仿皮草；如果询盘要的是真皮草，与对方的公开立场矛盾，先核实询盘是不是真的。

## 2. 主要市场规则（核验日期 2026-10）

| 市场 | 规则 | 对交易的影响 | 官方或主要来源 |
|---|---|---|---|
| 美国加州 | AB 44 自 2023-01-01 起禁止在州内销售新皮草制品（二手、宗教用途等有豁免） | 新真皮草 → `trade_blocker`；仿皮草不受影响 | https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=201920200AB44 |
| 美国部分城市 | 洛杉矶、旧金山、伯克利、西好莱坞等城市，以及马萨诸塞州多个城镇已禁售 | 按最终销售城市核对 | 倡导组织汇总（需到当地政府核实）：https://www.peta.org/features/fur-bans-fur-free-future/ |
| 美国全国 | 《皮草产品标签法》要求标签和发票写明动物名、是否染色、原产国、RN 或公司名 | 不是禁令，但吊牌和发票必须合规 | https://www.ftc.gov/business-guidance/resources/how-comply-fur-products-labeling-act |
| 美国（羊毛/羊绒） | 《羊毛产品标签法》要求如实标注纤维含量；对羊绒有专门要求 | 羊绒含量虚标属于高风险 | https://www.ftc.gov/business-guidance/resources/cachet-cashmere-complying-wool-products-labeling-act |
| 欧盟 | 第 1523/2007 号条例：禁止猫皮、狗皮的进口、出口和上市销售 | 物种命名必须准确 | https://eur-lex.europa.eu/eli/reg/2007/1523/oj/eng |
| 欧盟 | 第 1007/2009 号条例：限制海豹产品上市 | 海豹皮 → `trade_blocker` | https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex:32009R1007 |
| 欧盟 | 第 1007/2011 号条例：含"非纺织动物源部件"（毛领、皮草饰边）的纺织品必须在标签上注明 | 羊毛/羊绒外套配真毛领时，吊牌须标注 | https://eur-lex.europa.eu/eli/reg/2011/1007/oj/eng |
| 欧盟（待定） | 欧委会对公民倡议"Fur Free Europe"的回应一再推迟，可能的方案包括禁止养殖、禁止养殖并禁止上市 | 签长期合同前先查最新进展 | https://www.europarl.europa.eu/RegData/questions/reponses_qe/2026/000164/P10_RE(2026)000164_EN.pdf |
| 欧盟 | REACH：染色、整理所用化学品必须合规 | 出口欧盟必查 | ECHA 官方网站 |
| 瑞士 | 皮草申报条例：必须标明"真皮草"、物种、来源国、养殖或狩猎 | 吊牌信息必须完整 | https://www.blv.admin.ch/fr/fourrures |
| 英国 | 已禁止皮草养殖；截至 2026-10，进口和销售多数真皮草仍合法，禁售法案在议会讨论中 | 留意立法进展 | https://www.actasia.org/news/is-fur-banned-in-the-uk/ （倡导组织） |
| 挪威 | 皮草养殖禁令自 2025 年 2 月起全面生效（禁的是养殖，不是销售） | 不影响销售 | https://en.wikipedia.org/wiki/Fur_farming （需配合挪威官方信息） |
| 以色列 | 2021 年起禁止时尚用途的皮草销售 | 时尚类真皮草 → `trade_blocker` | https://www.npr.org/2021/06/14/1006279660/israel-has-become-the-first-country-to-ban-the-sale-of-fur-clothing |
| 全球 | CITES：物种列入附录的，需要许可证 | 常见养殖物种通常不在附录；野生来源或稀有物种必须查 | https://checklist.cites.org |

## 3. 行业身份核验点

### 拍卖行与认证（2026-10 现状）
- Saga Furs（芬兰）：正常运营，2026 年 12 月有线上拍卖：https://www.sagafurs.com/auction/
- Kopenhagen Fur：哥本哈根的最后一槌在 2024 年 6 月落下；目前改在波兰波兹南举办拍卖：https://www.kopenhagenfur.com
- Fur Harvesters Auction（加拿大北湾）：2026 年仍在举办拍卖：https://www.furharvesters.com
- NAFA（北美毛皮拍卖）：2019 年申请债权人保护后停止运营。对方自称"近年在 NAFA 拍得"→ 需要追问。
- Furmark（国际毛皮联合会 IFF 的认证与溯源体系，包含 WelFur 等动物福利项目）：https://www.furmark.com
- Origin Assured（OA，来源保证标签）：https://www.originassured.com

### 买家核验（零售商、品牌、批发商、买手）
- [ ] 有真实的经营场所（门店、showroom、仓库），可以用街景或登记地址核对
- [ ] 社媒有持续更新的产品内容和互动，成立年份与线上痕迹对得上
- [ ] 能说清楚最终销售市场，而且该市场允许销售所询品类
- [ ] 大额订单能提供以往的采购记录，例如拍卖采购凭证或现有供应商作为参考人
- [ ] 付款走公司对公账户；首单金额和定金比例按 `SETUP.md` 中设定的阈值执行

### 供应商核验（皮料、毛皮、加工）
- [ ] 养殖或加工许可，以及 WelFur、OA、Furmark 等认证（到认证方官网核对，而不只是看证书图片）
- [ ] 能提供从养殖场到批次的溯源文件
- [ ] 能提供出口所需的卫生证书、CITES 许可（如涉及）、REACH 合规声明
- [ ] 视频验厂或第三方验厂；报价远低于拍卖行情时需要追问

## 4. 行业 Red Flags
- 自称奢侈皮草品牌，但没有官网、社媒和电商店铺 → 先请对方自证身份。
- 买家所在地禁售真皮草，却大量采购真皮草 → 核实最终销售市场，或改推仿皮草。
- 声称有拍卖渠道，却拿不出任何采购记录 → 供应链存疑。
- 与询盘品类毫无关系的公司（比如激光厂、公交公司）来询皮草 → 高度疑似冒充，按 `../free-paths.md` 问题 1 用官方电话回拨核实。
- 以"免税、走私渠道、不开发票"等说法压价 → 合规和欺诈双重红旗。

## 5. 判定
- 最终销售地禁售 → `trade_blocker: true`，并在报告中给出替代方案：改推仿皮草、换市场，或只做可豁免的品类。
- 可以卖但需要标签或许可证 → 不设阻断，在"建议行动"里列出需要准备的文件。
- 仿皮草：禁售令一般不适用，但成分必须如实标注（美国执法案例里有把貉子毛标成仿皮草的）。
