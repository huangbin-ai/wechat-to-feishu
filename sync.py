#!/usr/bin/env python3
"""
公众号文章 → 飞书多维表格 每日同步脚本

通过 wewe-rss 获取微信公众号文章，自动同步到飞书多维表格。
支持去重、时间过滤、全文提取、噪声清洗。

配置方式（任选一种）：
  1. 环境变量（见下方 CONFIG）
  2. 配置文件 ~/.config/wechat-to-feishu/.env
"""
import json
import urllib.request
import urllib.parse
import re
import os
import sys
from datetime import datetime, timezone, timedelta

# ─── 配置（从环境变量或配置文件读取）─────────────────────

def load_env():
    """从配置文件加载环境变量"""
    env_file = os.path.expanduser("~/.config/wechat-to-feishu/.env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

load_env()

def require_env(key, desc):
    val = os.environ.get(key, "")
    if not val:
        print(f"❌ 缺少配置：{key}（{desc}）", file=sys.stderr)
        print(f"   请设置环境变量或写入 ~/.config/wechat-to-feishu/.env", file=sys.stderr)
        sys.exit(1)
    return val

WEWE_RSS_URL      = os.environ.get("WEWE_RSS_URL", "http://localhost:4000")
WEWE_AUTH         = require_env("WEWE_AUTH", "wewe-rss 认证码")
FEISHU_APP_ID     = require_env("FEISHU_APP_ID", "飞书应用 App ID")
FEISHU_APP_SECRET = require_env("FEISHU_APP_SECRET", "飞书应用 App Secret")
BITABLE_APP_TOKEN = require_env("BITABLE_APP_TOKEN", "飞书多维表格 App Token")
BITABLE_TABLE_ID  = require_env("BITABLE_TABLE_ID", "飞书多维表格 Table ID")

# 只同步最近 N 天的文章（0 = 不限时间，全量同步）
MAX_AGE_DAYS = int(os.environ.get("MAX_AGE_DAYS", "7"))
# ────────────────────────────────────────────────────

CST = timezone(timedelta(hours=8))


def http_get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def http_post(url, data, headers=None):
    body = json.dumps(data).encode()
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=body, headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def html_to_text(html):
    """提取微信文章正文段落，过滤头部导流噪声"""
    # 微信文章头部常见噪声关键词
    HEADER_NOISE = ('关注', '设为星标', '星标', '置顶', '右上角', '预计阅读',
                    'Original', '阅读原文', '点击关注', '扫码', '二维码',
                    '加入', '入群', '添加', '合作', '广告', '推广')

    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)

    # 提取 <p> 和 <section> 里的文字
    paras = re.findall(r'<(?:p|section)[^>]*>(.*?)</(?:p|section)>', html, re.DOTALL)
    texts = []
    for p in paras:
        t = re.sub(r'<[^>]+>', '', p)
        t = re.sub(r'&nbsp;', ' ', t)
        t = re.sub(r'&[a-zA-Z]+;', '', t)
        t = re.sub(r'[​‌‍﻿]', '', t)  # 零宽字符
        t = re.sub(r'\s+', ' ', t).strip()
        if len(t) > 8:
            texts.append(t)

    # 去相邻重复
    deduped = []
    for t in texts:
        if not deduped or t != deduped[-1]:
            deduped.append(t)

    # 过滤头部噪声段落（前5段里含噪声关键词的跳过）
    cleaned = []
    noise_count = 0
    for i, t in enumerate(deduped):
        if i < 6 and noise_count < 4 and any(kw in t for kw in HEADER_NOISE):
            noise_count += 1
            continue
        cleaned.append(t)

    result = '\n\n'.join(cleaned)

    if len(result) < 50:
        result = re.sub(r'<[^>]+>', '', html)
        result = re.sub(r'\s+', ' ', result).strip()

    return result[:5000]


def get_feishu_token():
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    r = http_post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal", data)
    return r["tenant_access_token"]


def get_existing_ids(token):
    """拉取飞书表格已有的文章 ID，用于去重"""
    url = (f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}"
           f"/tables/{BITABLE_TABLE_ID}/records?page_size=500")
    headers = {"Authorization": f"Bearer {token}"}
    existing = set()
    page_token = None
    while True:
        paged_url = url + (f"&page_token={page_token}" if page_token else "")
        r = http_get(paged_url, headers)
        for rec in r.get("data", {}).get("items", []):
            fields = rec.get("fields", {})
            link = fields.get("原文链接", "")
            if isinstance(link, list) and link:
                existing.add(link[0].get("link", ""))
            elif isinstance(link, str):
                existing.add(link)
        if not r.get("data", {}).get("has_more"):
            break
        page_token = r["data"].get("page_token")
    return existing


def write_to_feishu(token, records):
    """批量写入飞书多维表格"""
    url = (f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}"
           f"/tables/{BITABLE_TABLE_ID}/records/batch_create")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    for i in range(0, len(records), 100):
        batch = records[i:i+100]
        body = json.dumps({"records": batch}).encode()
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read().decode())
            created = len(result.get("data", {}).get("records", []))
            print(f"  写入 {created} 条")


def sync():
    print(f"\n{'='*50}")
    print(f"同步时间: {datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S')} CST")
    print(f"{'='*50}")

    # 1. 获取飞书 token
    token = get_feishu_token()
    print("✅ 飞书 token 获取成功")

    # 2. 获取已有文章链接（去重用）
    existing_links = get_existing_ids(token)
    print(f"📋 飞书已有 {len(existing_links)} 篇文章")

    # 3. 获取 wewe-rss 所有文章
    all_items = http_get(
        f"{WEWE_RSS_URL}/feeds/all.json",
        {"x-auth-code": WEWE_AUTH}
    ).get("items", [])
    print(f"📡 wewe-rss 共 {len(all_items)} 篇文章")

    # 4. 过滤：去重 + 时间范围
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    new_records = []

    for item in all_items:
        link = item.get("url", "")
        if not link or link in existing_links:
            continue

        # 时间过滤
        pub_str = item.get("date_published") or item.get("date_modified", "")
        if pub_str:
            try:
                pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                if pub_dt < cutoff:
                    continue
            except Exception:
                pass

        # 提取全文纯文本
        content_html = item.get("content_html", "")
        full_text = html_to_text(content_html)[:5000] if content_html else ""

        # 公众号名称
        account_name = ""
        author = item.get("author", {})
        if isinstance(author, dict):
            account_name = author.get("name", "")
        elif isinstance(author, str):
            account_name = author

        # 发布时间戳（毫秒）
        pub_ts = None
        if pub_str:
            try:
                pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                pub_ts = int(pub_dt.timestamp() * 1000)
            except Exception:
                pass

        today_ts = int(datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).timestamp() * 1000)

        record = {"fields": {
            "标题": item.get("title", "无标题"),
            "公众号": account_name,
            "原文链接": {"link": link, "text": item.get("title", link)},
            "全文": full_text,
        }}
        if pub_ts:
            record["fields"]["发布时间"] = pub_ts
        record["fields"]["采集日期"] = today_ts

        new_records.append(record)

    print(f"🆕 待写入 {len(new_records)} 篇新文章")

    if not new_records:
        print("✅ 无新内容，跳过写入")
        return

    # 5. 写入飞书
    write_to_feishu(token, new_records)
    print(f"✅ 同步完成，写入 {len(new_records)} 篇")


if __name__ == "__main__":
    sync()
