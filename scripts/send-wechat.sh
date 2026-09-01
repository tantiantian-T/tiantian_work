#!/usr/bin/env bash
# 薄封装：调用 send_wechat.py
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/scripts/send_wechat.py" "$@"
