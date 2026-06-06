# 公众号文章 → 飞书多维表格 自动同步

批量监测微信公众号，每天自动采集新文章，同步到飞书多维表格。

支持去重、时间过滤、全文提取，纯 Python 标准库零依赖。

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

- **批量监测** — 同时监测多个公众号，统一采集
- **自动同步** — 每天定时拉取新文章，写入飞书多维表格
- **智能去重** — 根据文章链接去重，不会重复写入
- **时间过滤** — 只同步最近 N 天的文章（默认 7 天）
- **全文提取** — 自动清洗 HTML，提取正文纯文本（去广告、去导流噪声）
- **零依赖** — 纯 Python 标准库，不需要安装任何第三方包

---

## 前置准备（约 20 分钟，只需做一次）

### 第一步：部署 wewe-rss

wewe-rss 是微信公众号的 RSS 服务，用 Docker 一条命令部署：

```bash
docker run -d \
  --name wewe-rss \
  -p 4000:4000 \
  -e AUTH_CODE=你的认证码 \
  -v $(pwd)/data:/app/data \
  cooderl/wewe-rss
```

部署完成后：

1. 浏览器打开 `http://localhost:4000`
2. 输入你设置的认证码登录
3. 点击「添加公众号」，用微信扫码授权
4. 添加你要监测的公众号（可以添加多个）

> 详细文档：https://github.com/cooderl/wewe-rss

### 第二步：创建飞书应用

1. 打开 [飞书开放平台](https://open.feishu.cn/app)，登录
2. 点击「创建企业自建应用」
3. 填写应用名称（如「公众号同步」），创建
4. 进入应用 → 「凭证与基础信息」，记录 **App ID** 和 **App Secret**
5. 进入「权限管理」→ 搜索并开通以下权限：
   - `bitable:app:readonly`（读取多维表格）
   - `bitable:app`（写入多维表格）
6. 点击「版本管理与发布」→ 创建版本 → 发布

### 第三步：创建飞书多维表格

1. 在飞书中新建一个「多维表格」
2. 创建以下字段：

| 字段名 | 类型 |
|--------|------|
| 标题 | 文本 |
| 公众号 | 文本 |
| 原文链接 | 超链接 |
| 全文 | 文本 |
| 发布时间 | 日期 |
| 采集日期 | 日期 |

3. 从表格 URL 中获取 **App Token**（`https://xxx.feishu.cn/base/` 后面的那串字符）
4. 点击表格左下角的表名 → 右键 → 复制链接，从中获取 **Table ID**
5. 在表格右上角「...」→「更多」→「添加文档应用」，搜索并添加你刚创建的飞书应用

---

## 安装

```bash
git clone https://github.com/huangbin-ai/wechat-to-feishu.git
cd wechat-to-feishu
chmod +x install.sh
./install.sh
```

首次运行 `install.sh` 会生成配置文件模板，按提示编辑填入你的实际值：

```bash
vim ~/.config/wechat-to-feishu/.env
```

填完后再次运行 `install.sh`，脚本会：

1. ✅ 检查 Python、Docker、wewe-rss 环境
2. ✅ 验证配置是否正确
3. ✅ 测试运行同步脚本
4. ✅ 自动注册 cron 定时任务（每天 08:00 执行）

## 配置项说明

| 变量 | 说明 | 示例 |
|------|------|------|
| `WEWE_RSS_URL` | wewe-rss 服务地址 | `http://localhost:4000` |
| `WEWE_AUTH` | wewe-rss 认证码 | 你部署时设置的 AUTH_CODE |
| `FEISHU_APP_ID` | 飞书应用 App ID | `cli_xxxxxxxxx` |
| `FEISHU_APP_SECRET` | 飞书应用 App Secret | `xxxxxxxxxxxxxxx` |
| `BITABLE_APP_TOKEN` | 飞书多维表格 App Token | 从表格 URL 获取 |
| `BITABLE_TABLE_ID` | 飞书多维表格 Table ID | `tblxxxxxxxxx` |
| `MAX_AGE_DAYS` | 同步最近几天的文章 | `7`（默认） |

## 日常使用

安装完成后**不需要任何操作**，每天 08:00 自动执行。

```bash
# 手动执行一次
python3 sync.py

# 查看运行日志
tail -f ~/Library/Logs/wechat-to-feishu.log

# 查看定时任务
crontab -l | grep wechat
```

## 底层依赖

- [wewe-rss](https://github.com/cooderl/wewe-rss) — 微信公众号 RSS 服务
- [飞书开放平台](https://open.feishu.cn/) — 多维表格 API

## License

MIT
