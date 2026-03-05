#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$ROOT_DIR/venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "错误: 未找到虚拟环境 Python: $PYTHON_BIN"
  echo "请先执行: python3 -m venv venv && ./venv/bin/pip install -r requirements.txt"
  exit 1
fi

if [[ $# -ne 1 ]]; then
  echo "用法: $0 <polymarket_url>"
  echo "示例: $0 \"https://polymarket.com/sports/valorant/val-555-fcy-2026-03-05\""
  exit 1
fi

URL="$1"
exec "$PYTHON_BIN" "$ROOT_DIR/main.py" "$URL"
