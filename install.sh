#!/bin/bash
# 公众号文章同步 — 安装脚本
# 检查环境、生成配置、注册定时任务
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_DIR="$HOME/.config/wechat-to-feishu"
ENV_FILE="$CONFIG_DIR/.env"
LOG_FILE="$HOME/Library/Logs/wechat-to-feishu.log"
PYTHON3="$(command -v python3 || true)"

echo ""
echo "═══════════════════════════════════════════════"
echo "  公众号文章 → 飞书多维表格 自动同步 安装脚本"
echo "═══════════════════════════════════════════════"
echo ""

# ── 1. 检查 Python ────────────────────────────────────

if [[ -z "$PYTHON3" ]]; then
  echo "❌ 未找到 python3，请先安装：brew install python3"
  exit 1
fi
echo "✅ Python3: $PYTHON3"

# ── 2. 检查 Docker ────────────────────────────────────

if command -v docker &>/dev/null; then
  echo "✅ Docker: $(docker --version | head -1)"
else
  echo "⚠️  未找到 Docker（wewe-rss 需要 Docker 运行）"
  echo "   安装地址：https://www.docker.com/products/docker-desktop/"
fi

# ── 3. 检查 wewe-rss ──────────────────────────────────

WEWE_URL="${WEWE_RSS_URL:-http://localhost:4000}"
if curl -s --max-time 3 "$WEWE_URL" >/dev/null 2>&1; then
  echo "✅ wewe-rss: 运行中 ($WEWE_URL)"
else
  echo "⚠️  wewe-rss 未运行 ($WEWE_URL)"
  echo "   部署方法见 README 的「前置准备」部分"
fi

# ── 4. 生成配置文件 ───────────────────────────────────

echo ""
if [[ -f "$ENV_FILE" ]]; then
  echo "✅ 配置文件已存在：$ENV_FILE"
  echo "   如需修改：vim $ENV_FILE"
else
  mkdir -p "$CONFIG_DIR"
  cp "$SCRIPT_DIR/.env.example" "$ENV_FILE"
  echo "📝 配置文件已生成：$ENV_FILE"
  echo ""
  echo "   ⚠️  请先编辑配置文件，填入你的实际值："
  echo "   vim $ENV_FILE"
  echo ""
  echo "   填完后重新运行此脚本。"
  exit 0
fi

# ── 5. 验证配置是否已填写 ─────────────────────────────

source "$ENV_FILE" 2>/dev/null || true

MISSING=0
for VAR in WEWE_AUTH FEISHU_APP_ID FEISHU_APP_SECRET BITABLE_APP_TOKEN BITABLE_TABLE_ID; do
  VAL="${!VAR:-}"
  if [[ -z "$VAL" || "$VAL" == "你的"* ]]; then
    echo "❌ 配置未填写：$VAR"
    MISSING=1
  fi
done

if [[ $MISSING -eq 1 ]]; then
  echo ""
  echo "请编辑配置文件后重新运行：vim $ENV_FILE"
  exit 1
fi
echo "✅ 配置项检查通过"

# ── 6. 测试同步脚本 ──────────────────────────────────

echo ""
echo "⏳ 测试运行同步脚本..."
if $PYTHON3 "$SCRIPT_DIR/sync.py" 2>&1; then
  echo ""
  echo "✅ 同步脚本运行正常"
else
  echo ""
  echo "❌ 同步脚本运行失败，请检查配置和 wewe-rss 状态"
  exit 1
fi

# ── 7. 注册 cron 定时任务 ─────────────────────────────

echo ""
CRON_CMD="0 8 * * * cd $SCRIPT_DIR && $PYTHON3 sync.py >> $LOG_FILE 2>&1"

# 检查是否已存在
if crontab -l 2>/dev/null | grep -q "wechat-to-feishu"; then
  echo "✅ cron 定时任务已存在，跳过"
else
  # 追加到 crontab
  (crontab -l 2>/dev/null; echo "# 公众号文章同步 - 每天 8:00") | crontab -
  (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
  echo "✅ cron 定时任务已注册（每天 08:00 执行）"
fi

# ── 完成 ──────────────────────────────────────────────

echo ""
echo "═══════════════════════════════════════════════"
echo "  安装完成！"
echo ""
echo "  📋 配置文件：$ENV_FILE"
echo "  📄 运行日志：$LOG_FILE"
echo "  ⏰ 定时任务：每天 08:00 自动同步"
echo ""
echo "  手动执行：python3 $SCRIPT_DIR/sync.py"
echo "  查看日志：tail -f $LOG_FILE"
echo "═══════════════════════════════════════════════"
