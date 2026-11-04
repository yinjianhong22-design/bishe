# 03 黑白名单 —— 说明与现状

对应需求：F1.3 号码/网址黑白名单比对（命中黑名单直接高风险、白名单直接安全）。

## 已落地 ✅

### blacklist_url/openphish_feed_20261103.txt

- 来源：OpenPhish 社区版实时 feed（https://openphish.com/feed.txt）
- 抓取时间：2026-11-03，约 250 条活跃钓鱼 URL
- 用途：网址黑名单种子库；运行根目录 `download_datasets.py` 可刷新为最新快照（`openphish_feed_latest.txt`）

## 脚本下载 ⬇️

| 数据 | 来源 | 说明 |
|---|---|---|
| URLHaus 在线恶意 URL | https://urlhaus.abuse.ch/downloads/csv_online/ | abuse.ch 维护的恶意 URL 库，CSV 格式（`#` 开头为注释行），含 URL / 状态 / 威胁类型 / 标签，**比 OpenPhish 更全**，建议作为 URL 黑名单主库 |
| Tranco Top-1M 域名 | https://tranco-list.eu/top-1m.csv.zip | 研究界标准的域名流行度榜（聚合多个榜单、抗操纵），取前 N 名（如前 10 万）作**域名白名单** |
| OpenPhish 最新 feed | https://openphish.com/feed.txt | 脚本会重新抓取覆盖 |

## 空缺与替代方案 ⚠️

### 1. 电话号码黑名单 —— 无权威开源库

出于隐私原因，**不存在公开的真实诈骗电话号码数据库**（国内 12321 举报数据、运营商黑产号码库均不开放）。方案：
- 用 `blacklist_phone/测试号码_seed.txt` 中的**构造测试号码**（号段合法、Luhn/位长合规，但非真实号码）支撑功能联调与实验；
- 论文中如实说明：电话黑名单以合成数据验证机制，不声称真实覆盖率。

### 2. IP 黑名单

需求中提及 IP 维度，但反诈场景下 URL/域名为主、IP 为辅。如需补充可手动下载：
- abuse.ch Feodo Tracker（C2 IP）：https://feodotracker.abuse.ch/downloads/ipblocklist.txt
- 非必需，视进度决定。

### 3. 更全的钓鱼库（可选，需注册）

- PhishTank：https://phishtank.org/ —— 免费但需注册申请 API key，审核 1–2 天。OpenPhish + URLHaus 已够用，非必需。
- Kaggle "Malicious URLs" 数据集：https://www.kaggle.com/datasets/sid321axn/malicious-urls-dataset（需 Kaggle 登录）
- UCI PhiUSIIL 钓鱼 URL 数据集：https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset（含特征标注，适合做特征分析实验）
