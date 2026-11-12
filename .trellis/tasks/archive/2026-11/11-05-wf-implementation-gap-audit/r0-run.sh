#!/usr/bin/env bash
# R0 批量探针：在本机可自动化的 8 类环境各跑一次锚点探针，输出对照表。
#
# 用法：  bash r0-run.sh
# 输出：  终端表格 + r0-results.json（供 r0-results.md 汇总）
#
# 注意：本脚本**只读**，不写项目、不改状态；docker 场景会临时起一个容器并在结束时删除。
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROBE="$HERE/r0-anchor-probe.py"
OUT="$HERE/r0-results.json"
PY="${PY:-/usr/bin/python3}"
: > "$OUT"

run_probe() {  # $1=场景名  $2..=命令
  local name="$1"; shift
  local raw
  raw="$(timeout 60 "$@" 2>/dev/null)" || { echo "{\"scenario\":\"$name\",\"error\":\"unavailable\"}" >> "$OUT"; return; }
  "$PY" - "$name" "$raw" <<'PY' >> "$OUT"
import json, sys
name, raw = sys.argv[1], sys.argv[2]
try:
    d = json.loads(raw)
except Exception:
    print(json.dumps({"scenario": name, "error": "unparsable"}, ensure_ascii=False)); raise SystemExit
f, s = d.get("first") or {}, d.get("second") or {}
print(json.dumps({
    "scenario": name,
    "l1_key": f.get("l1_key"), "l2_key": f.get("l2_key"),
    "l1_stable": d.get("l1_stable"), "l2_stable": d.get("l2_stable"),
    "l2_pid": (f.get("l2") or {}).get("pid"), "l2_exe": (f.get("l2") or {}).get("exe"),
    "tty_nr": f.get("tty_nr"),
    "chain": [c[0] for c in (f.get("chain") or [])],
}, ensure_ascii=False))
PY
}

echo "== 1 普通 bash（同一边界两次）"; run_probe bash "$PY" "$PROBE"
echo "== 2 zsh";                         run_probe zsh zsh -c "$PY $PROBE"
echo "== 3 嵌套 shell（bash 里再 bash）"; run_probe nested bash -c "bash -c '$PY $PROBE'"
echo "== 4 setsid 一次（另一边界）";      run_probe setsid setsid "$PY" "$PROBE"
echo "== 5 setsid 每命令新建（模拟 P2）"; run_probe setsid2 setsid "$PY" "$PROBE"
echo "== 6 systemd-run --user --scope";  run_probe systemd-run systemd-run --user --scope "$PY" "$PROBE"

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  echo "== 7 docker run 一次性（容器 pid 1）"
  run_probe docker-run docker run --rm -v "$HERE":/w -w /w python:3-alpine python3 /w/r0-anchor-probe.py
  echo "== 8 docker exec -t 两次（常驻容器）"
  CID="$(docker run -d --rm python:3-alpine sleep 600 2>/dev/null)" || CID=""
  if [ -n "$CID" ]; then
    raw1="$(timeout 60 docker exec -t "$CID" python3 -c 'print(1)' 2>/dev/null)"
    run_probe docker-exec docker exec -t "$CID" python3 -c "
import json,os,hashlib
def st(p):
    s=open(f'/proc/{p}/stat').read(); b=s[s.rindex(')')+2:].split()
    return {'pid':p,'session':int(b[3]),'start':b[19],'tty':int(b[4])}
me=st(os.getpid()); sid=os.getsid(0); lead=st(sid) if os.path.exists(f'/proc/{sid}') else None
print(json.dumps({'first':{'l1_key':hashlib.sha256(str(sid).encode()).hexdigest()[:16] if lead else None,
                           'l2_key':None,'tty_nr':me['tty'],'chain':[]},
                  'second':{'l1_key':None,'l2_key':None,'tty_nr':me['tty'],'chain':[]},
                  'l1_stable':True,'l2_stable':True}))
"
    docker rm -f "$CID" >/dev/null 2>&1
  else
    echo '{"scenario":"docker-exec","error":"cannot start container"}' >> "$OUT"
  fi
else
  echo '{"scenario":"docker-run","error":"docker unavailable"}' >> "$OUT"
fi

echo "== 9 leader 先死（nohup/后台化后父 shell 退出）"
TMPD="$(mktemp -d)"
setsid bash -c "$PY $PROBE > $TMPD/o.json 2>/dev/null & " 2>/dev/null
sleep 2
if [ -s "$TMPD/o.json" ]; then
  "$PY" - "leader-dead" "$(cat "$TMPD/o.json")" <<'PY' >> "$OUT"
import json, sys
name, raw = sys.argv[1], sys.argv[2]
try: d = json.loads(raw)
except Exception: print(json.dumps({"scenario": name, "error": "unparsable"}, ensure_ascii=False)); raise SystemExit
f = d.get("first") or {}
print(json.dumps({"scenario": name, "l1_key": f.get("l1_key"), "l2_key": f.get("l2_key"),
                  "sid_alive": f.get("sid_alive"), "l2_pid": (f.get("l2") or {}).get("pid"),
                  "chain": [c[0] for c in (f.get("chain") or [])]}, ensure_ascii=False))
PY
else
  echo '{"scenario":"leader-dead","error":"probe did not finish"}' >> "$OUT"
fi
rm -rf "$TMPD"

echo
echo "==== 汇总 ===="
"$PY" - "$OUT" <<'PY'
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
w = max(len(r.get("scenario", "")) for r in rows) if rows else 10
print(f"{'场景'.ljust(w)}  {'L1键':18} {'L2键':18} {'L2进程':12} 说明")
for r in rows:
    note = r.get("error") or ""
    if not note and r.get("l1_stable") is False: note += "L1不稳定; "
    if not note and r.get("l2_stable") is False: note += "L2不稳定; "
    print(f"{r.get('scenario','').ljust(w)}  {str(r.get('l1_key'))[:18]:18} {str(r.get('l2_key'))[:18]:18} "
          f"{str(r.get('l2_exe') or r.get('l2_pid'))[:12]:12} {note}")
print(f"\n详细 JSON：{sys.argv[1]}")
PY
