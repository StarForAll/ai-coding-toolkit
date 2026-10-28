"""Apply v49 version metadata, then generate records with discovered line numbers."""
import json
import re
from pathlib import Path
from prepare_v49 import ROOT, REC, MAIN, COMP, SPEC, GUIDE


def line_of(path, phrase, occurrence=1):
    lines = (ROOT / path).read_text().splitlines()
    found = [i for i, line in enumerate(lines, 1) if phrase in line]
    assert len(found) >= occurrence, (path, phrase, found)
    return found[occurrence - 1]


def apply_versions():
    main = (ROOT / MAIN).read_text()
    comp = (ROOT / COMP).read_text()
    if 'version: v49' in main and 'version: v49' in comp:
        return
    assert main.count('version: v48') == 1
    main = main.replace('version: v48', 'version: v49', 1)
    assert main.count('# 工作流整体设计（v48 · 修订）') == 1
    main = main.replace('# 工作流整体设计（v48 · 修订）', '# 工作流整体设计（v49 · 修订）', 1)
    main = main.replace('；v49 修复：族表纳入返工加边、挂起子态补向前动作、路径族与类型 5 归档条件化、配套移交门', '', 1)
    # This is the one authored status suffix. If it exists, this script has already run.
    status_end = main.index('\nscope:')
    status = main[main.index('status:'):status_end]
    assert 'v49 修复：' not in status
    main = main[:status_end] + '；v49 修复：族表纳入返工加边、挂起子态补向前动作、路径族与类型 5 归档条件化、配套移交门' + main[status_end:]
    section10_start = main.index('## 10. 演进规则')
    section10_end = main.index('\n---', section10_start)
    section10 = main[section10_start:section10_end]
    old_a = '模块的 `implements_design` 必须等于本文件 frontmatter 版本（v48）'
    old_b = '配套文档的 `design` 字段必须写明本文件版本（`workflow-design.md v48`）'
    assert section10.count(old_a) == 1 and section10.count(old_b) == 1
    section10 = section10.replace(old_a, old_a.replace('v48', 'v49'))
    section10 = section10.replace(old_b, old_b.replace('v48', 'v49'))
    main = main[:section10_start] + section10 + main[section10_end:]
    anchor = '### v48\n'
    assert main.count(anchor) == 1
    (ROOT / MAIN).write_text(main)

    assert comp.count('version: v48') == 1
    comp = comp.replace('version: v48', 'version: v49', 1)
    assert comp.count('design: workflow-design.md v48') == 2
    comp = comp.replace('design: workflow-design.md v48', 'design: workflow-design.md v49', 1)
    old_header = '(./workflow-design.md) v48 同步'
    assert comp.count(old_header) == 1
    comp = comp.replace(old_header, '(./workflow-design.md) v49 同步', 1)
    (ROOT / COMP).write_text(comp)


def insert_records():
    main_path = ROOT / MAIN
    main = main_path.read_text()
    # Allow a deliberate rerun after anchor-label edits without duplicating records.
    if '### v49\n' in main:
        a=main.index('### v49\n'); b=main.index('### v48\n',a)
        main=main[:a]+main[b:]
    entries = [
        ('族表与注记（主稿 §4.4）', MAIN, '| **活动期建边后随前置归档** | **建边 / 返工加边**'),
        ('口径 10⑤ 枚举（主稿 §0.1）', MAIN, '产生路径族括号：任务定义（创建期写 deps / 收尾重定义）'),
        ('口径 10⑤ 第二枚举（主稿 §0.1）', MAIN, '（任务定义 / 继承 / 建边与返工加边 / 重连四类）'),
        ('挂起路由下沉源（§9.1 第二段）', MAIN, '按第三段的下沉规则先开工该未完成前置'),
        ('接手镜像（§8.4）', MAIN, '按 §9.1 第二段的对应行先开工该未完成前置'),
        ('组合表出口（主稿 §7.7）', MAIN, '前置不全正常时按 §9.1 第二段对应行开工该未完成前置'),
        ('组合表镜像（配套）', COMP, '前置不全正常时按主设计 §9.1 第二段对应行'),
        ('路由说明区（§9.1）', MAIN, '指针无效或为空时先走第二段（有挂起任务时）：'),
        ('返工下沉自检（主稿 §10）', MAIN, '一次挂起任务在返工期间被加入未完工前置'),
        ('类型5补建幂等条件（主稿 §7.7）', MAIN, '已归档者不重复归档'),
        ('基线变更局部范围（主稿 §5.5）', MAIN, '本步不为旧任务新增出口'),
        ('配套移交场景门（配套 §12）', COMP, '完成旧口径移交确认后按同一条件补做'),
        ('探针块版本与新增命令', SPEC, '# v49 additions'),
        ('方法义务25', GUIDE, '25. **枚举成员全集'),
        ('方法义务26', GUIDE, '26. **「按 §N」必须落到命中行'),
    ]
    locations = [(label, path, line_of(path, phrase)) for label, path, phrase in entries]
    lines = [
        '### v49',
        '',
        '- **修正来源**：第二轮同类面扫描识别到族2缺返工加边、挂起且R已归档但前置未完成时无可命中的对账类型；按状态入口与唯一引用源修正文及接手 / 配套投影。其余来源为P1路径族枚举分类、P2已归档输入的归档幂等说明、P3断言限缩至本步、P4配套场景补旧口径移交门。',
        '- **源**：主稿 §4.4（M1/M2）、§0.1口径10⑤两处（M3/M4）、§9.1第二段（M5）、§8.4（M6）、§7.7组合表（M7a）、§9.1说明（M8）、§10自检（M9）、§7.7类型5两处（M10a/M10b）、§5.5（M11）、配套 §12场景（M12）；对应位点均在下方按路径/行号列出。',
        '- **副本**：M3/M4为主稿内双枚举；M7a由配套 §8 组合表行（M7b）镜像；M12在配套 §12；M14探针与 M14b 注册表同步；Guide 25/26记录对应方法义务。',
        '- **当前源与验收位（路径 / 行号由本任务记录脚本生成）**：',
    ]
    for label, path, line in locations:
        lines.append(f'  - {label} 已同步（{path}:{line}）。')
    lines += [
        '- **副本核对**：口径 10⑤ 两份枚举、§9.1 / §8.4 / §7.7 组合表与配套 §8 场景、§10 自检、spec 探针及 guide 方法义务均列入本版 fix-notes 与 `review-report-v2.md`。',
        '- 版本 v49；配套 `design: workflow-design.md v49`；第一轮审查报告保留，第二轮轴与修复结论见当前任务 research。',
        '',
    ]
    entry = '\n'.join(lines)
    marker = '### v48\n'
    assert main.count(marker) == 1
    main_path.write_text(main.replace(marker, entry + marker, 1))

    comp_path = ROOT / COMP
    comp = comp_path.read_text()
    if '## 37. 本版修订（v49）' in comp:
        comp=comp[:comp.index('## 37. 本版修订（v49）')].rstrip()+'\n'
    lines = [
        '', '## 37. 本版修订（v49）', '',
        '本版配套镜像以主设计的唯一规则源为准，不另行定义条件或动作顺序：前置来源见主设计 §4.4，入口与挂起路由见 §9.1，修复出口见 §7.7 / §6.4，执行场景见 §10。',
        '- 挂起组合行（配套 §8）已同步（docs/workflows/依赖机制设计说明.md:' + str(line_of(COMP, '| 未归档 + 挂起（任意前置）')) + '）。',
        '- 返工完成场景门（配套 §12）已同步（docs/workflows/依赖机制设计说明.md:' + str(line_of(COMP, '完成旧口径移交确认后按同一条件补做')) + '）。',
        '- 版本 v49；`design: workflow-design.md v49`；与主设计 v49 同版。',
    ]
    comp_path.write_text(comp + '\n'.join(lines) + '\n')


if __name__ == '__main__':
    apply_versions()
    insert_records()
