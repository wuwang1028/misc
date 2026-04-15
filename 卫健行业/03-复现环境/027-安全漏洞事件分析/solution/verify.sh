#!/bin/sh
set -eu

base_url="${1:-http://127.0.0.1:8080}"

echo "[1/3] 检查首页可访问性"
curl -fsS "$base_url/" >/dev/null

echo "[2/3] 检查 file.php 触发点存在"
curl -fsS "$base_url/file.php?c=/etc/passwd" | grep -Eq 'file exists|file not exists'

echo "[3/3] 检查主题切换入口存在"
curl -fsS -I "$base_url/theme.php" >/dev/null

echo "027 复现环境基础检查通过"
