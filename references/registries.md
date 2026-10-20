# 商事登记与税号核验入口（46 个国家/地区 + 5 个离岸辖区）

身份核验时阅读。先查官方登记，再用聚合平台补充。入口打不开时，在报告中注明"入口失效"，换用聚合平台，或请客户提供注册证书；不要凭记忆补链接。核验日期：2026-10。

## 查询通用技巧

- **用注册号查，不用公司名查。** 先让客户提供注册号或税号，再去官方入口反查。号码查询不受语言和拼写影响，最准。
- **名称用原文。** 越南语、土耳其语等，去掉声调符号也能查到；阿拉伯语、俄语，用原文或注册号查询，再用 `scripts/screen_prep.py` 生成拉丁转写，供制裁筛查使用。
- **外语界面。** 用浏览器整页翻译即可，字段对照见文末"标准化字段"。
- **访问受限。** 部分官方站点会拦截境外 IP 或自动访问。遇到时换用聚合平台（OpenCorporates、GLEIF），或让客户导出登记页截图，再选一两项关键信息独立复核。
- **收费入口。** 标"部分收费"的，一般基础状态免费、详细档案收费。快筛只看免费部分即可。

## 税号与海关编码

| 用途 | 入口 | 说明 |
|---|---|---|
| 欧盟 VAT 号 | https://ec.europa.eu/taxation_customs/vies/ | 返回有效或无效；部分国家同时返回登记名称和地址 |
| 欧盟 EORI 号 | https://ec.europa.eu/taxation_customs/dds2/eos/eori_validation.jsp | 进口商应有 EORI |
| 英国 VAT 号 | https://www.tax.service.gov.uk/check-vat-number/enter-vat-details | 返回登记名称和地址 |
| 印度 GSTIN | https://services.gst.gov.in/services/searchtp | 15 位 GSTIN，返回法定名称、状态、登记日期 |
| 秘鲁 RUC | https://www.gob.pe/565-consultar-ruc | 11 位 RUC，返回状态和地址 |

## 欧洲

| 国家/地区 | 入口 | 查询提示 |
|---|---|---|
| 欧盟跨国检索 | https://e-justice.europa.eu/topics/registers-business-insolvency-land/business-registers-search-company-eu_en | 不确定在哪国注册时先用这个 |
| 英国 | https://find-and-update.company-information.service.gov.uk | 8 位公司号；可免费查董事、实际控制人（PSC）、年报 |
| 爱尔兰 | https://cro.ie/services-and-help/core/ | CRO 公司号 |
| 德国 | https://www.handelsregister.de | 按 HRB/HRA 编号和所属法院查询；基础信息免费 |
| 法国 | https://annuaire-entreprises.data.gouv.fr | 9 位 SIREN；免费 |
| 意大利 | https://www.registroimprese.it | 部分收费；可配合 VAT 号查询 |
| 西班牙 | https://www.registradores.org ；https://www.boe.es/diario_borme/ | 用 CIF/NIF 查；官方公报 BORME 免费 |
| 荷兰 | https://www.kvk.nl/zoeken | 8 位 KVK 号 |
| 比利时 | https://kbopub.economie.fgov.be | 10 位企业号 |
| 瑞士 | https://www.zefix.ch | 用 CHE 开头的企业识别号查 |
| 丹麦 | https://datacvr.virk.dk | 8 位 CVR；境外可能被拦截 |
| 挪威 | https://www.brreg.no | 9 位组织号 |
| 芬兰 | https://www.ytj.fi | Y-tunnus 编号 |
| 希腊 | https://www.businessportal.gr | GEMI 编号 |
| 波兰 | https://wyszukiwarka-krs.ms.gov.pl | 用 KRS 号或 NIP 税号查 |
| 土耳其 | https://mersis.gtb.gov.tr ；https://www.ticaretsicil.gov.tr | 土耳其语界面；贸易登记公报（TTSG）可查设立、变更公告 |
| 俄罗斯 | https://egrul.nalog.ru | 用 ИНН 或 ОГРН 查；俄罗斯客户必须同时按 `screening.md` 做强化筛查 |

## 美洲

| 国家/地区 | 入口 | 查询提示 |
|---|---|---|
| 美国 | 注册州的州务卿（Secretary of State）网站；https://opencorporates.com ；上市公司查 https://www.sec.gov/edgar/search/ | 没有全国统一的登记处，先确认注册州（常见为特拉华州） |
| 加拿大 | https://ised-isde.canada.ca/cbr-rec/ | 联邦和大部分省份的登记 |
| 墨西哥 | https://siem.economia.gob.mx/ | 经济部企业信息系统；可配合 RFC 税号核验 |
| 巴西 | https://www.receita.economia.gov.br | 用 14 位 CNPJ 查 |
| 哥伦比亚 | https://www.rues.org.co/RUES_Web/consultas | 用 NIT 或名称查商会登记 |
| 秘鲁 | https://www.gob.pe/565-consultar-ruc | 见税号表 |

## 亚太

| 国家/地区 | 入口 | 查询提示 |
|---|---|---|
| 中国大陆 | https://www.gsxt.gov.cn | 用 18 位统一社会信用代码查；对方有中国母公司、办事处或采购代理时查 |
| 中国香港 | https://www.e-services.cr.gov.hk | 公司注册处电子服务；查询公司资料收少量费用 |
| 日本 | https://www.houjin-bangou.nta.go.jp | 13 位法人番号；有英文界面 |
| 韩国 | https://dart.fss.or.kr ；https://www.iros.go.kr | DART 可查上市及外审公司的披露信息；法院登记处可查全部法人（部分收费） |
| 新加坡 | https://www.bizfile.gov.sg | 用 UEN 查；基础信息免费 |
| 马来西亚 | https://www.ssm.com.my ；https://www.ssm-einfo.my | 用 12 位注册号查；e-Info 档案收费 |
| 泰国 | https://datawarehouse.dbd.go.th | 用 13 位法人号查；可切换英文 |
| 越南 | https://dangkykinhdoanh.gov.vn | 用 10 位企业代码（即税号 MST）查；境外访问可能较慢 |
| 印尼 | https://ahu.go.id ；https://oss.go.id | 名称检索免费，档案收费；OSS 可核对 NIB 营业编号 |
| 菲律宾 | https://checkwithsec.sec.gov.ph ；https://bnrs.dti.gov.ph | 公司查 SEC，个体商号查 DTI |
| 印度 | https://www.mca.gov.in/content/mca/global/en/mca/master-data/MDS.html | 用 21 位 CIN 查；同时核对 GSTIN |
| 巴基斯坦 | https://secpportal.com.pk/secp-company-search | SECP 登记检索（第三方入口，结果需向官方复核） |
| 孟加拉国 | https://app.roc.gov.bd/psp/nc_search | RJSC 的名称检索（主要用于查名称是否已被注册），详细档案需申请 |
| 澳大利亚 | https://abr.business.gov.au ；https://connectonline.asic.gov.au | 先用 11 位 ABN 查，再用 ASIC 的 9 位 ACN 查公司状态和董事 |

## 中东与非洲

| 国家/地区 | 入口 | 查询提示 |
|---|---|---|
| 阿联酋 | https://u.ae/en/information-and-services/business/important-digital-services/national-economic-register ；执照核验 https://u.ae/en/information-and-services/business/important-digital-services/inquire-about-licences-names-and-activities | 本土公司按酋长国查营业执照；40 多个自由区各有自己的登记处，先问清楚对方在哪个自由区 |
| 沙特 | https://mc.gov.sa | 以阿拉伯语界面为主，可切换英文；用 10 位商业登记号（CR）查最准，请客户提供 CR 证书 |
| 卡塔尔 | https://www.moci.gov.qa/en/trade-search | 商工部商号检索 |
| 科威特 | https://www.moci.gov.kw/en/e-service/ | 商业登记电子服务，阿拉伯语为主 |
| 阿曼 | https://www.business.gov.om/ieasy/wp/en/ | Invest Easy 平台 |
| 埃及 | http://itda.gov.eg/en/registry-inquiry-en.html | 商业登记查询（按次收费） |
| 尼日利亚 | https://www.cac.gov.ng/services/company-search | 用 RC 号或名称查；尼日利亚的预付款诈骗高发，必须配合 `free-paths.md` 的自证清单 |
| 肯尼亚 | https://brs.go.ke | 商业登记服务 |
| 南非 | https://eservices.cipc.co.za/Search.aspx | CIPC 登记 |
| 加纳 | https://orc.gov.gh/service-entity-information-search.php | ORC 实体信息检索 |

## 离岸辖区

BVI、开曼、百慕大、巴拿马、塞舌尔的做法见 `dimensions.md` 第 2 节。

## 聚合与辅助

- OpenCorporates：https://opencorporates.com，跨国聚合，适合查曾用名和关联公司。
- GLEIF 法人识别码（LEI）检索：https://search.gleif.org，官方免费，可查法定名称、地址、母公司。
- Bizapedia：https://www.bizapedia.com，美国各州登记的汇总，查到后再去州官方网站复核。
- 域名注册信息：https://lookup.icann.org；网站历史：https://web.archive.org
- 更多免费替代路径（财报、诉讼、社媒透明度、付款核验、信息匮乏地区）见 `free-paths.md`。

## 标准化字段（各国结果统一写成这样）

| 字段 | 填写方式 |
|---|---|
| 法定名称 | 原文 + 英文（或拉丁转写） |
| 注册号 | 号码 + 类型（如 CR、CNPJ、SIREN、UEN、CIN） |
| 注册日期 / 状态 | YYYY-MM-DD；状态统一写成"存续 / 注销 / 停业 / 清算中 / 未知" |
| 法人类型 | 原文 + 中文（如 GmbH = 有限责任公司） |
| 注册地址 | 原文；另注明是否为注册代理地址或共享地址 |
| 董事 / 签字人 | 姓名 + 职务 + 任职日期（不写出生日期） |
| 来源 | 入口 URL + 访问日期 |
