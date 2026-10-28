"""Freeze the v48 baseline and exact, user-approved v49 replacements."""
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
REC = Path(__file__).resolve().parent
MAIN = 'docs/workflows/workflow-design.md'
COMP = 'docs/workflows/依赖机制设计说明.md'
SPEC = '.trellis/spec/docs/index.md'
GUIDE = '.trellis/spec/guides/design-review-thinking-guide.md'
ROWS = []


def row(ident, path, anchor, old, new, acceptance, reason):
    ROWS.append(dict(ID=ident, 文件=path, 锚点=anchor, old=old, new=new,
                     验收位=acceptance, 说明=reason))


row('M1', MAIN, '§4.4 族2',
    '| **活动期建边后随前置归档** | **建边**建于两端都在活动区时，前置一侧随后归档，边继续有效 | 是 |',
    '| **活动期建边后随前置归档** | **建边 / 返工加边**（两端都在活动区时建立的边）——前置一侧随后归档，边继续有效 | 建边为是；返工加边按其自身守卫（§6.4） |',
    'probe **建边 / 返工加边**=1；D1', 'F1 源')
row('M2', MAIN, '§4.4 族注记',
    '- 族 2 只覆盖建边，重连产生的边归族 4；同一路径可同时属族 1 与族 4 时，判定以是否继承为准（两者同为合法来源）。',
    '- 族 2 覆盖建边与返工加边，重连产生的边归族 4；同一路径可同时属族 1 与族 4 时，判定以是否继承为准（两者同为合法来源）。',
    'M1 镜像行；D1', 'F1 源注记')
row('M3', MAIN, '§0.1 口径10⑤',
    '（产生路径族括号：任务定义（创建期写 deps / 收尾重定义 / 基线变更新建）/ 继承 / 建边 / 重连）',
    '（产生路径族括号：任务定义（创建期写 deps / 收尾重定义）/ 继承（含基线变更新建）/ 建边与返工加边 / 重连）',
    'D1；M4 枚举镜像', 'F1/P1')
row('M4', MAIN, '§0.1 口径尾段',
    '（任务定义 / 继承 / 建边 / 重连四类）',
    '（任务定义 / 继承 / 建边与返工加边 / 重连四类）',
    'probe 建边与返工加边 / 重连四类=1；M3', 'P1')
row('M5', MAIN, '§9.1 挂起表第3行',
    '| 存在返工任务记录、无未归档 R，但 T 的前置集合不全正常 | 按 §7.7 对账；异常前置按 §7.4 处置 |',
    '| 存在返工任务记录、无未归档 R，但 T 的前置集合不全正常 | 按第三段的下沉规则先开工该未完成前置（同进行中目标的处置），完成后回本段按 §6.4 第 5 步清挂起；该前置为“异常”按 §7.4、为“正常但未归档”按类型 3；链上无就绪任务时报告阻塞 |',
    'probe 开工该未完成前置=4；M9 场景；D2/D3', 'F2 源')
row('M6', MAIN, '§8.4 挂起第3条',
    '存在返工任务记录、无未归档 R、但前置集合不全正常 → 按 §7.7 对账；异常前置按 §7.4 处置；',
    '存在返工任务记录、无未归档 R、但前置集合不全正常 → 按 §9.1 第二段的对应行先开工该未完成前置，完成后回本段清挂起；该前置为异常按 §7.4、为“正常但未归档”按类型 3；',
    'probe 开工该未完成前置=4；M5', 'F2 引用')
row('M7a', MAIN, '§7.7 组合表挂起行出口',
    '§6.4 评估 / 进入 R；前置不全正常时按挂起阶段的对账行',
    '§6.4 评估 / 进入 R；前置不全正常时按 §9.1 第二段对应行开工该未完成前置，完成后回本段清挂起',
    'probe 开工该未完成前置=4；D2/D3', 'F2 组合表')
row('M7b', COMP, '§8 组合表挂起行出口',
    '主设计 §6.4 评估 / 进入 R；前置不全正常时按挂起阶段的对账行',
    '主设计 §6.4 评估 / 进入 R；前置不全正常时按主设计 §9.1 第二段对应行（下沉开工该未完成前置）',
    'M7a 镜像行；墓碑probe=0', 'F2 镜像')
row('M8', MAIN, '§9.1 说明区',
    '指针无效或为空时先走第二段（有挂起任务时），再按第三段选择就绪任务。',
    '指针无效或为空时先走第二段（有挂起任务时）：第二段命中后按该行处置，其中需要选择就绪任务的（第 3 行的下沉）按第三段的排序规则执行；无挂起任务时按第三段选择。',
    'M5/M9；D2/D3', 'F2 命中即停与行内下沉分域')
row('M9', MAIN, '§10 自检场景唯一锚点',
    '一次放弃收尾任务（删边变体）',
    '一次挂起任务在返工期间被加入未完工前置（迭代期建边）→ 返工完成后不清挂起 → 按 §9.1 第二段开工该未完成前置 → 前置完成后清挂起 → 继续 T → 一次放弃收尾任务（删边变体）',
    '自检场景；probe 开工该未完成前置=4；D3', 'F2；new 包含 old：验证完整新句和屏蔽新句后旧锚点=0')
row('M10a', MAIN, '§7.7 类型5补建',
    '继任者已建（无论账本值，含已为异常）时只补齐重连；最后归档旧任务。',
    '继任者已建（无论账本值，含已为异常）时只补齐重连；最后归档旧任务（已归档者不重复归档）。',
    'probe 已归档者不重复归档=2；类型1 P窗口', 'P2')
row('M10b', MAIN, '§7.7 类型5无指向',
    '**无替换指向**（有原因、无指向）：补齐下游删边与旧任务归档——识别按字段，不枚举来源；',
    '**无替换指向**（有原因、无指向）：补齐下游删边与旧任务归档（已归档者不重复归档）——识别按字段，不枚举来源；',
    'probe 已归档者不重复归档=2；类型1一般分支', 'P2')
row('M11', MAIN, '§5.5 轻量用法',
    '它的出口只有两个：按正常流程完成收尾，或在下一次基线变更时重新按本步判定。',
    '本步不为旧任务新增出口：按正常流程完成收尾，或在下一次基线变更时重新按本步判定。',
    'probe 本步不为旧任务新增出口=1', 'P3')
row('M12', COMP, '§12 返工完成场景行',
    '| 返工完成 | R 收尾时评估并清除 T 的挂起；启动时按同一条件补做，覆盖 4→5 崩溃窗口 |',
    '| 返工完成 | R 收尾时评估并清除 T 的挂起；启动时在完成旧口径移交确认后按同一条件补做，覆盖 4→5 崩溃窗口 |',
    'probe 完成旧口径移交确认后按同一条件补做=1；§6.3镜像', 'P4')


def table_rows(text, header):
    lines = text.splitlines()
    start = lines.index(header) + 2
    out = []
    while start < len(lines) and lines[start].startswith('|'):
        out.append(lines[start]); start += 1
    return out


def main():
    target = REC / 'baseline.json'
    if target.exists():
        raise SystemExit('Baseline already exists; refusing to overwrite evidence')
    texts = {p: (ROOT / p).read_text() for p in (MAIN, COMP, SPEC, GUIDE)}
    checks = []
    for item in ROWS:
        result = subprocess.run(['grep', '-F', '-c', '--', item['old'], str(ROOT / item['文件'])],
                                text=True, capture_output=True, check=False)
        count = int(result.stdout.strip() or '0')
        assert count == 1, (item['ID'], count)
        checks.append(dict(ID=item['ID'], grep_line_count=count,
                           substring_count=texts[item['文件']].count(item['old'])))
    design_count = texts[COMP].count('design: workflow-design.md v48')
    assert design_count == 2
    main_text = texts[MAIN]
    headers = {
        '族表': ('| 族 | 内容 | 受 §7.5 建边限制 |', 4),
        '矩阵': ('| 写入路径 | 写入时点 | 指向终值 | 说明 / 原因终值 | 依据 |', 14),
        '组合表': ('| 组合 | 判定 | 出口 |', 12),
        '表4-2': ('| # | 从 | 到 | 触发 | 写入者 / 说明 |', 7),
        '窗口': ('| 窗口 | 已提交识别项 / 残留 | 恢复 |', 9),
    }
    counts = {}
    for name, (header, expected) in headers.items():
        counts[name] = len(table_rows(main_text, header))
        assert counts[name] == expected
    for path in (MAIN, COMP):
        assert re.search(r'^version: v48$', texts[path], re.M)
    report = REC / 'review-report.md'
    baseline = {
        'git_status': subprocess.check_output(['git', 'status', '--porcelain=v1'], cwd=ROOT, text=True),
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'expected_head': '870d9d7',
        'expected_head_diff': subprocess.check_output(['git', 'diff', '--stat', '870d9d7', 'HEAD', '--', *texts], cwd=ROOT, text=True),
        'versions': {p: 'v48' for p in (MAIN, COMP)}, 'counts': counts,
        'sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in texts},
        'original_review_sha256': hashlib.sha256(report.read_bytes()).hexdigest(),
        'texts': texts, 'old_checks': checks, 'companion_design_count': design_count,
    }
    target.write_text(json.dumps(baseline, ensure_ascii=False, indent=2) + '\n')
    with (REC / 'fix-manifest.tsv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=list(ROWS[0]), delimiter='\t')
        writer.writeheader(); writer.writerows(ROWS)
    print(json.dumps({k:v for k,v in baseline.items() if k!='texts'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
