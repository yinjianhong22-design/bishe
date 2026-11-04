# -*- coding: utf-8 -*-
"""
download_datasets.py — 一键补齐本项目所需的外部公开数据集
=========================================================

用法（在本目录 datasets/ 下执行）：
    python download_datasets.py

仅使用 Python 标准库（urllib / zipfile），无需安装任何依赖。
所有文件下载到本脚本所在目录（datasets/）的对应分类子目录中。
单个文件下载失败不会中断整体流程，最后输出汇总。

覆盖内容：
  1. FBS_SMS 伪基站垃圾短信数据集（GitHub: Cypher-Z/FBS_SMS_Dataset，13 个类别文件 + README）
  2. SpamMessage 中文垃圾短信（GitHub: hrwhisper/SpamMessage，带标签 58MB / 不带标签 14MB）
  3. ChiFraud 中文欺诈文本数据集（GitHub: xuemingxxx/ChiFraud，train 47MB + t2022 + t2023）
  4. OpenPhish 钓鱼 URL 实时 feed
  5. URLHaus 在线恶意 URL CSV
  6. Tranco Top-1M 域名白名单（zip 自动解压出 top-1m.csv）
"""

import os
import sys
import time
import zipfile
import urllib.request
import urllib.error
import urllib.parse

BASE = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) dataset-fetcher/1.0"}

results = []  # (描述, 是否成功, 备注)


def log(msg):
    print(msg, flush=True)


def download(url, dest, desc="", timeout=300):
    """下载单个文件，返回是否成功。已存在且非空则跳过。"""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        log(f"[跳过] {desc or os.path.basename(dest)}（已存在 {os.path.getsize(dest)/1024:.0f} KB）")
        results.append((desc, True, "已存在，跳过"))
        return True
    log(f"[下载] {desc or os.path.basename(dest)}")
    log(f"       {url}")
    tmp = dest + ".part"
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r, open(tmp, "wb") as f:
            total = 0
            t0 = time.time()
            while True:
                chunk = r.read(1 << 20)  # 1MB
                if not chunk:
                    break
                f.write(chunk)
                total += len(chunk)
                log(f"\r       ... {total/1024/1024:.1f} MB", )
        os.replace(tmp, dest)
        log(f"       ✅ 完成 {total/1024/1024:.2f} MB，耗时 {time.time()-t0:.0f}s -> {dest}")
        results.append((desc, True, f"{total/1024/1024:.2f} MB"))
        return True
    except Exception as e:
        if os.path.exists(tmp):
            os.remove(tmp)
        log(f"       ❌ 失败: {e}")
        results.append((desc, False, str(e)))
        return False


def gh_raw(owner, repo, path, dest, desc=""):
    """从 GitHub raw 下载，自动尝试 main / master 分支。"""
    quoted = urllib.parse.quote(path)
    for branch in ("main", "master"):
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{quoted}"
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                if r.status == 200:
                    return download(url, dest, desc)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            log(f"       ❌ HTTP {e.code}: {url}")
            results.append((desc, False, f"HTTP {e.code}"))
            return False
        except Exception as e:
            log(f"       ❌ {e}")
            results.append((desc, False, str(e)))
            return False
    log(f"       ❌ main/master 分支均未找到: {path}")
    results.append((desc, False, "404 main/master"))
    return False


# ----------------------------------------------------------------------
# 1. FBS_SMS 伪基站垃圾短信数据集（13 个类别文件 + README）
#    论文: Lies in the Air (CCS'20)，引用请标注来源
# ----------------------------------------------------------------------
FBS_DIR = os.path.join(BASE, "01_诈骗短信", "FBS_SMS")
FBS_FILES = [
    # (仓库内文件名, 本地文件名)  —— 文件名含 ':'，Windows 下不合法，统一改为 '_'
    ("FR:Financial",           "FR_Financial.txt"),
    ("FR:Other",               "FR_Other.txt"),
    ("FR:Phishing(Bank)",      "FR_Phishing_Bank.txt"),      # 296KB，银行钓鱼，最相关
    ("FR:Phishing(Other)",     "FR_Phishing_Other.txt"),     # 45KB，高度重复，见 README
    ("AD:Loan",                "AD_Loan.txt"),
    ("AD:Retail",              "AD_Retail.txt"),             # 812KB
    ("AD:Network_service",     "AD_Network_service.txt"),    # 657KB
    ("AD:Other",               "AD_Other.txt"),
    ("AD:Real_estate",         "AD_Real_estate.txt"),
    ("IL:Gambling",            "IL_Gambling.txt"),           # 230KB
    ("IL:Fake_ID_and_invoice", "IL_Fake_ID_and_invoice.txt"),
    ("IL:Political_propaganda","IL_Political_propaganda.txt"),
    ("IL:Escort_service",      "IL_Escort_service.txt"),
    ("Other",                  "Other.txt"),
]

def fetch_fbs():
    log("\n===== 1/6 FBS_SMS 伪基站垃圾短信 =====")
    for src, local in FBS_FILES:
        gh_raw("Cypher-Z", "FBS_SMS_Dataset", src,
               os.path.join(FBS_DIR, local), f"FBS_SMS/{local}")
    gh_raw("Cypher-Z", "FBS_SMS_Dataset", "README.md",
           os.path.join(FBS_DIR, "README_upstream.md"), "FBS_SMS/README_upstream.md")


# ----------------------------------------------------------------------
# 2. SpamMessage 中文垃圾短信（带标签约 58MB，不带标签约 14MB）
# ----------------------------------------------------------------------
def fetch_spammessage():
    log("\n===== 2/6 SpamMessage 中文垃圾短信 =====")
    d = os.path.join(BASE, "01_诈骗短信", "SpamMessage")
    gh_raw("hrwhisper", "SpamMessage", "data/带标签短信.txt",
           os.path.join(d, "带标签短信.txt"), "SpamMessage/带标签短信.txt")
    gh_raw("hrwhisper", "SpamMessage", "data/不带标签短信.txt",
           os.path.join(d, "不带标签短信.txt"), "SpamMessage/不带标签短信.txt")


# ----------------------------------------------------------------------
# 3. ChiFraud 中文欺诈文本数据集（CC BY-NC 4.0，仅供研究）
# ----------------------------------------------------------------------
def fetch_chifraud():
    log("\n===== 3/6 ChiFraud 中文欺诈文本 =====")
    d = os.path.join(BASE, "02_案例库", "ChiFraud")
    for name in ("ChiFraud_train.csv", "ChiFraud_t2022.csv", "ChiFraud_t2023.csv"):
        gh_raw("xuemingxxx", "ChiFraud", f"dataset/{name}",
               os.path.join(d, name), f"ChiFraud/{name}")


# ----------------------------------------------------------------------
# 4. OpenPhish 钓鱼 URL feed（社区版实时快照）
# ----------------------------------------------------------------------
def fetch_openphish():
    log("\n===== 4/6 OpenPhish 钓鱼 URL feed =====")
    d = os.path.join(BASE, "03_黑白名单", "blacklist_url")
    download("https://openphish.com/feed.txt",
             os.path.join(d, "openphish_feed_latest.txt"),
             "OpenPhish feed（最新快照）")


# ----------------------------------------------------------------------
# 5. URLHaus 在线恶意 URL（CSV，# 开头为注释行）
# ----------------------------------------------------------------------
def fetch_urlhaus():
    log("\n===== 5/6 URLHaus 恶意 URL =====")
    d = os.path.join(BASE, "03_黑白名单", "blacklist_url")
    download("https://urlhaus.abuse.ch/downloads/csv_online/",
             os.path.join(d, "urlhaus_online.csv"),
             "URLHaus csv_online（当前在线恶意 URL）")


# ----------------------------------------------------------------------
# 6. Tranco Top-1M 域名白名单（zip -> 解压出 top-1m.csv）
# ----------------------------------------------------------------------
def fetch_tranco():
    log("\n===== 6/6 Tranco Top-1M 白名单 =====")
    d = os.path.join(BASE, "03_黑白名单", "whitelist_domain")
    zpath = os.path.join(d, "tranco_top1m.csv.zip")
    if download("https://tranco-list.eu/top-1m.csv.zip", zpath, "Tranco top-1m.zip"):
        csv_path = os.path.join(d, "tranco_top1m.csv")
        try:
            with zipfile.ZipFile(zpath) as z:
                names = [n for n in z.namelist() if n.endswith(".csv")]
                with z.open(names[0]) as src, open(csv_path, "wb") as dst:
                    dst.write(src.read())
            os.remove(zpath)
            log(f"       ✅ 已解压 -> {csv_path}")
        except Exception as e:
            log(f"       ❌ 解压失败: {e}（zip 保留在 {zpath}）")


def main():
    t0 = time.time()
    fetch_fbs()
    fetch_spammessage()
    fetch_chifraud()
    fetch_openphish()
    fetch_urlhaus()
    fetch_tranco()

    log("\n" + "=" * 60)
    log("下载汇总")
    log("=" * 60)
    ok = sum(1 for _, s, _ in results if s)
    for desc, success, note in results:
        log(f"  {'✅' if success else '❌'}  {desc}  ——  {note}")
    log(f"\n成功 {ok}/{len(results)}，总耗时 {time.time()-t0:.0f}s")
    if ok < len(results):
        log("失败项可稍后重跑本脚本（已存在的文件会自动跳过），或按 README 中的链接手动下载。")
        sys.exit(1)


if __name__ == "__main__":
    main()
