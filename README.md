# 公众号文章 → 飞书多维表格 自动同步

每天自动抓取微信公众号新文章，同步到飞书多维表格，支持去重、时间过滤、全文提取。

## 工作原理

```
微信公众号
    ↓ 微信账号授权登录
wewe-rss（本机 Docker）
    ↓ RSS/JSON 接口
Python 同步脚本
    ↓ 飞书 API
飞书多维表格
    ↑
cron 每天 8:00 触发
```

## 功能

- **自动同步** — 定时从 wewe-rss 拉取公众号文章，写入飞书多维表格
- **智能去重** — 根据文章链接去重，不会重复写入
- **时间过滤** — 只同步最近 N 天的文章（默认 7 天）
- **全文提取** — 自动清洗 HTML，提取正文纯文本（去广告、去导流噪声）
- **零依赖** — 纯 Python 标准库，不需要安装任何第三方包

## 前置条件

1. **wewe-rss** 已部署并运行（Docker）：https://github.com/cooderl/wewe-rss
2. **飞书应用** 已创建，获取 App ID 和 App Secret
3. **飞书多维表格** 已创建，包含以下字段：

| 字段名 | 类型 |
|--------|------|
| 标题 | 文本 |
| 公众号 | 文本 |
| 原文链接 | 超链接 |
| 全文 | 文本 |
| 发布时间 | 日期 |
| 采集日期 | 日期 |

## 安装

```bash
git clone https://github.com/huangbin-ai/wechat-to-feishu.git
cd wechat-to-feishu
```

## 配置

```bash
# 复制配置模板
mkdir -p ~/.config/wechat-to-feishu
cp .env.example ~/.config/wechat-to-feishu/.env

# 编辑配置，填入你的实际值
vim ~/.config/wechat-to-feishu/.env
```

也可以用环境变量：

```bash
export WEWE_AUTH=你的认证码
export FEISHU_APP_ID=你的App_ID
export FEISHU_APP_SECRET=你的App_Secret
export BITABLE_APP_TOKEN=你的表格Token
export BITABLE_TABLE_ID=你的表格Table_ID
```

## 使用

### 手动运行

```bash
python3 sync.py
```

### 定时任务（cron）

```bash
crontab -e
```

添加一行（每天 8:00 执行）：

```
0 8 * * * cd /path/to/wechat-to-feishu && python3 sync.py >> ~/Library/Logs/wechat-to-feishu.log 2>&1
```

## 底层依赖

- [wewe-rss](https://github.com/cooderl/wewe-rss) — 微信公众号 RSS 服务
- [飞书开放平台](https://open.feishu.cn/) — 多维表格 API

## License

MIT
