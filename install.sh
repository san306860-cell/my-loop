#!/usr/bin/env bash
# 安装一份共享正文，为本机宿主建立兼容链接。
set -euo pipefail
exec python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts/install.py" "$@"
