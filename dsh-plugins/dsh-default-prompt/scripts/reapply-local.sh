#!/usr/bin/env bash
# 从本仓库的 dsh-plugins/dsh-default-prompt 恢复「本会话定制版」到 web profile。
#
# 用途：`dsh plugin update` / `pnpm install` 会把 node_modules 里的插件换成上游版本，
# 覆盖掉 dsh-purge 联动开关、文本按钮、自定义文件路径等改动。更新后执行本脚本即可还原。
#
# 用法：bash dsh-plugins/dsh-default-prompt/scripts/reapply-local.sh
# 生效：重启 dsh web（模块源码不在 HMR 监听范围内）。
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DST="$HOME/.dsh/profiles/web/node_modules/dsh-default-prompt"

[ -f "$SRC/index.js" ] || { echo "仓库副本不存在或已损坏: $SRC" >&2; exit 1; }
[ -d "$DST" ] || { echo "未找到已安装插件: $DST" >&2; exit 1; }

ts="$(date +%Y%m%d-%H%M%S)"
backup="$DST.bak-before-reapply-$ts"

cp -a "$DST" "$backup"
rm -rf "$DST"
cp -a "$SRC/." "$DST"
rm -rf "$DST/scripts"

echo "已从仓库副本恢复: $DST"
echo "旧副本备份:        $backup"
echo "重启 dsh web 后生效。"
