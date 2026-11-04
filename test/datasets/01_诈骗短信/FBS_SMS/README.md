# FBS_SMS 伪基站垃圾短信数据集 — 本地说明

## 来源

- 仓库：https://github.com/Cypher-Z/FBS_SMS_Dataset
- 论文：Yiming Zhang 等, *Lies in the Air: Characterizing Fake-base-station Spam Ecosystem in China*, ACM CCS 2020. https://doi.org/10.1145/3372297.3417257
- 规模：约 14,000 条中国伪基站实发垃圾短信，研究人员人工标注 14 个类别。
- 使用要求：引用上述 CCS'20 论文并注明来源链接。

## 数据特点（重要）

- 文本已做**分词预处理**（字/词之间有空格），建模或规则匹配前需决定是否去除空格。
- 隐私匿名化占位符：`NAME`（人名）、`PLACE`（地名）、`DIGIT`（数字）、`URL`、`PHONE`、`CELLPHONE`、`BANK`（银行卡号）、`WECHAT`、`QQ`、`HOTLINE`。
  - 对**实体抽取测试集**的影响：手机号、卡号、链接已被替换为占位符，只能用于验证"占位符级"的抽取规则；真实形态的实体需从其他来源（如自行收集）补充。
- 文件名中的 `:` 在 Windows 不合法，本地保存时统一改为 `_`（如 `FR:Phishing(Bank).txt` → `FR_Phishing_Bank.txt`）。

## 类别前缀含义

- `FR` = Fraud（诈骗）：最贴合本项目"风险核验"正样本
- `AD` = Advertising（垃圾广告）：可作灰样本/干扰样本
- `IL` = Illegal（违法内容）：赌博、假证等，可作高风险类别

## 本地已存放文件

| 本地文件 | 源文件 | 状态 |
|---|---|---|
| FR_Financial.txt | FR:Financial.txt（33 KB） | ✅ 完整 |
| FR_Other.txt | FR:Other.txt（87 KB） | ✅ 完整；含航班取消、中奖、相册木马链接、换号诈骗等 |
| AD_Loan.txt | AD:Loan.txt（43 KB） | ✅ 完整；贷款/代办信用卡广告，建议作灰样本 |
| FR_Phishing_Other_dedup.txt | FR:Phishing(Other).txt（45 KB） | ⚠️ **去重版**：源文件约 95% 是同一条"联通流量话费"钓鱼短信的重复，仅保留 8 条不重复样本；完整版请运行根目录 download_datasets.py 或 git clone 原仓库 |

## 其余类别文件（体积较大，未直接存放）

`FR:Phishing(Bank).txt`（296 KB，**银行钓鱼类，与本项目最相关**）、`AD:Retail.txt`（812 KB）、`AD:Network_service.txt`（657 KB）、`IL:Gambling.txt`（230 KB）、`AD:Other.txt`（145 KB）、`IL:Fake_ID_and_invoice.txt`（59 KB）、`IL:Political_propaganda.txt`（59 KB）、`AD:Real_estate.txt`（54 KB）、`IL:Escort_service.txt`（13 KB）等。

→ 运行 `datasets/download_datasets.py` 可一键拉取全部文件到本目录。
