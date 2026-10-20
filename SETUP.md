# 首次使用配置

## 1. 公司标识
本包不含任何公司或个人标识。报告署名在出报告时由使用者填写。

## 2. 设定你的风控阈值
填写下表。技能执行时以这里的数字为准：

| 项目 | 你的设定 | 参考 |
|---|---|---|
| 新客户首单上限 | [填写，如 USD 2,000] | 按产品单价和承受能力设定 |
| 🟡 客户定金比例 | [填写，如 30%] | 常见做法是 30% 定金 + 70% 见提单副本 |
| 个人定制单定金比例 | [填写，如 50%] | 定制件无法转卖，建议更高 |
| 需要升级为深调的金额 | [填写，如 USD 10,000] | 超过这个金额自动建议深调 |
| 默认复查周期 | [填写，如 90 天] | 对应 `dd_ledger.py add --review-days`；🔴 客户固定不超过 30 天 |

## 3. 选择评分权重
运行 `python3 scripts/risk_score.py --presets` 查看预设：
- `default`：通用外贸
- `project_b2b`：建材、工程、设备等项目型 B2B（诉讼、经营年限权重更高）
- `ecommerce`：跨境电商、零售卖家（数字口碑权重更高）

在评分 JSON 里写 `"weights": "project_b2b"` 即可使用预设，也可以写成 `{维度: 权重}` 的完全自定义形式。7 个维度合计必须为 1，制裁权重不得低于 0.20；不符合时脚本会拒绝计算。

## 4. 行业插件
- 已有插件：`references/industry/fur-trade.md`（皮草、仿皮草、动物纤维）、`references/industry/project-b2b.md`（建材、工程、设备）。
- 其他行业：复制 `references/industry/_template.md` 新建插件，并在 `SKILL.md` 第二步第 6 条加一行引用。

## 5. 安装
把 `customer-background-investigation/` 整个文件夹放进你所用 AI 助手的技能目录。在对话中说"背调""尽调""KYC""制裁筛查""这个客户靠谱吗""这个供应商可信吗"等即可触发。

## 6. 脚本（纯 Python 标准库，不需要安装任何依赖，也不需要 API Key）
| 脚本 | 作用 | 自测 |
|---|---|---|
| `scripts/domain_check.py` | 识别仿冒邮箱和网站：看形似度、域名年龄、是否为免费邮箱 | `--selftest` |
| `scripts/screen_prep.py` | 制裁筛查准备：生成名称变体（音译、后缀、西里尔字母转写）、检索清单和 CSV 结果表 | `--selftest` |
| `scripts/risk_score.py` | 统一评分：支持预设权重和自定义权重，含一票否决规则 | `--selftest` |
| `scripts/dd_ledger.py` | 背调台账：建档、历史对比、到期复查提醒 | `--selftest` |
| `scripts/report_check.py` | 交付前自检：来源数量、残留占位符、未获取清单、筛查留痕、评级与付款、台账；任一项不过即不予交付 | `--selftest` |

台账默认保存为当前目录下的 `dd_ledger.csv`，可以用 `--ledger` 指定其他路径。台账只追加记录，不覆盖历史。

## 7. 维护
入口链接和法规会变化。`references/` 中的表格都标了核验日期；每半年复查一次链接，并更新 `references/industry/` 中的法规状态。
