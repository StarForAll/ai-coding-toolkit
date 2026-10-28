"""Merge the v50 fix manifest and generate version-record line references."""
import csv
import sys
from pathlib import Path

ROOT = Path('/home/xzc/projects/personal/ai-coding-toolkit')
REC = ROOT / '.trellis/tasks/10-28-workflow-design-v48-0-1-audit/research'
sys.path.insert(0, str(REC))
import apply_v50 as source_edits
import apply_v50_followup as followup_edits

MAIN = 'docs/workflows/workflow-design.md'
COMP = 'docs/workflows/依赖机制设计说明.md'
SPEC = '.trellis/spec/docs/index.md'
GUIDE = '.trellis/spec/guides/design-review-thinking-guide.md'


def line_of(path, needle, occurrence=1):
    lines = (ROOT / path).read_text().splitlines()
    hits = [i for i, line in enumerate(lines, 1) if needle in line]
    assert len(hits) >= occurrence, (path, needle, hits)
    return hits[occurrence - 1]


def prepare_manifest():
    rows = [dict(item) for item in source_edits.REPLACEMENTS + followup_edits.edits]
    main_text = (ROOT / MAIN).read_text()
    comp_text = (ROOT / COMP).read_text()
    main_start, main_end = main_text.index('### v50\n'), main_text.index('### v49\n')
    comp_start = comp_text.index('## 38. 本版修订（v50）\n')
    rows += [
        dict(ID='pending-main-appendix', 文件=MAIN, 锚点='Appendix C v50 insertion',
             old='<INSERTION before ### v49>', new=main_text[main_start:main_end],
             验收位='D4 record/body grep + generated line references', 说明='M13; script-generated appendix record'),
        dict(ID='pending-companion-appendix', 文件=COMP, 锚点='companion §38 v50 insertion',
             old='<INSERTION at end after §37>', new='\n' + comp_text[comp_start:],
             验收位='D4 record/body grep + generated line references', 说明='M13; script-generated companion record'),
    ]
    by_anchor = {row['锚点']: row for row in rows}
    assert len(by_anchor) == len(rows), 'duplicate manifest anchors'

    # These two entries modify a full source-record line / insert a block.
    status_new = next(line for line in (ROOT / MAIN).read_text().splitlines() if line.startswith('status:'))
    v50_suffix = '；v50 修复：类型 5 终归档调用逐点加守卫、挂起前置递归匹配本段、族 2 标题与成员对齐、修订记录源副本归类更正'
    assert status_new.endswith(v50_suffix)
    by_anchor['status suffix']['old'] = status_new[:-len(v50_suffix)]
    by_anchor['status suffix']['new'] = status_new

    copy_old = 'M3/M4为主稿内双枚举；M7a由配套 §8 组合表行（M7b）镜像；'
    copy_new = 'M3/M4为主稿内双枚举；§8.4（M6）为引用式接手摘要；M7a由配套 §8 组合表行（M7b）镜像；'
    by_anchor['Appendix C v49 copy classification']['old'] = copy_old
    by_anchor['Appendix C v49 copy classification']['new'] = copy_new

    # This is an insertion before the v46 probe-table heading; the old text is
    # an insertion-point descriptor rather than a text being deleted.
    probe_text = (ROOT / SPEC).read_text()
    probe_start = probe_text.index('# v50 additions')
    probe_end = probe_text.index(chr(96)*3, probe_start)
    by_anchor['v50 regression probes']['old'] = '<INSERTION: before #### v46 probe table>'
    by_anchor['v50 regression probes']['new'] = probe_text[probe_start:probe_end]
    rows.append(dict(ID='probe-archive-lines', 文件=SPEC, 锚点='archive guard probe expectation',
                     old='rg -n "已归档者不重复归档" docs/workflows/workflow-design.md   # 2 hits: type-5 build and no-pointer branches',
                     new=next(line for line in probe_text.splitlines() if line.startswith('rg -n "已归档者不重复归档"')),
                     验收位='rg -n=4 lines; rg -o=5 occurrences; four named type-5 branches',
                     说明='v50新增两处守卫及统一类型1同类词面；匹配行4与出现次数5分列'))

    # Assign a compact, deterministic sequence to the combined source and mirror edits.
    for number, row in enumerate(rows, 1):
        row['ID'] = f'V50-{number:02d}'

    path = REC / 'fix-manifest-v50.tsv'
    with path.open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=['ID','文件','锚点','old','new','验收位','说明'], delimiter='\t')
        writer.writeheader()
        writer.writerows(rows)
    return rows


def append_main_record():
    path = ROOT / MAIN
    text = path.read_text()
    start_marker, end_marker = '### v50\n', '### v49\n'
    if start_marker in text:
        start = text.index(start_marker)
        end = text.index(end_marker, start)
        text = text[:start] + text[end:]

    entries = [
        ('族 2 标题与成员（§4.4）', MAIN, '| **活动期建边 / 返工加边后随前置归档** |'),
        ('类型 5 补建终归档（§7.7）', MAIN, '最后归档旧任务（已归档者不重复归档）'),
        ('类型 5 改判放弃终归档（§7.7）', MAIN, '改判放弃-P 行不新增写入'),
        ('类型 5 无指向终归档（§7.7）', MAIN, '**无替换指向**（有原因、无指向）'),
        ('类型 1同类归档守卫措辞（§7.7）', MAIN, '补齐删边（已归档者不重复归档）'),
        ('挂起返工子任务递归入口（§9.1第二段行1）', MAIN, 'R 自身挂起时以 R 为“对应 T”'),
        ('挂起下沉前置状态全集（§9.1第二段行3）', MAIN, '前置本身挂起时，以它为“对应 T”'),
        ('接手摘要递归引用（§8.4）', MAIN, '递归处理该未完成前置（其本身挂起时以其为本段上下文）'),
        ('主稿挂起组合表引用（§7.7）', MAIN, '前置不全正常时按 §9.1 第二段对应行递归处理'),
        ('配套挂起组合表引用（§8）', COMP, '前置不全正常时按主设计 §9.1 第二段对应行递归处理'),
        ('挂起递归自检（§10）', MAIN, 'Q 自身挂起且有未归档 R_Q'),
        ('说明区分支范围（§9.1）', MAIN, '下沉是『当前任务』行与第二段第 3 行内的分支'),
        ('挂起状态递归清除判据（§9.1）', MAIN, '满足 §6.4 第 5 步按第 2 行清除该前置的挂起'),
        ('返工子任务自身挂起入口（§9.1）', MAIN, 'R 自身挂起时以 R 为“对应 T”回到本段并匹配各行'),
        ('v49源记录更正（附录C）', MAIN, '§9.1第二段（M5，唯一规则源）'),
        ('v49副本记录更正（附录C）', MAIN, '§8.4（M6）为引用式接手摘要'),
        ('v50探针组', SPEC, '# v50 additions'),
        ('Guide 25 同动作调用位例', GUIDE, '同一动作全集还须逐调用位配对验收'),
        ('主稿当前版本断言（§10）', MAIN, '模块的 `implements_design` 必须等于本文件 frontmatter 版本（v50）'),
        ('配套当前版本断言（§10）', MAIN, '配套文档的 `design` 字段必须写明本文件版本（`workflow-design.md v50`）'),
    ]
    generated = [(label, file, line_of(file, anchor)) for label, file, anchor in entries]
    lines = [
        '### v50', '',
        '- **修正来源**：v50复核确认类型5有四个终归档调用，两个改判放弃分支缺幂等条件；§9.1下沉目标可能自身挂起，原第二段未递归匹配其入口；同版修正族2名称，并把§8.4 / 配套§8维持为引用式副本。P6并入类型5调用全集核查；P5更正v49记录的源/副本分类。',
        '- **唯一规则源**：主稿 §7.7 类型5定义最终归档动作及其守卫；主稿 §9.1 第二段定义挂起上下文与递归入口；§4.4 定义归档前置来源族。',
        '- **副本 / 引用位**：§8.4、主稿 §7.7挂起组合行、配套 §8组合行引用§9.1第二段；路径族探针与Guide 25提供机械验收。附录C v49源记录纠正为§9.1第二段，§8.4归入引用式副本。',
        '- **源与验收位（文件行号由 `finalize_v50_records.py` 生成）**：',
    ]
    for label, file, line in generated:
        lines.append(f'  - {label} 已同步（{file}:{line}）。')
    lines += [
        '- **版本**：主稿与配套均为v50；配套 `design` pin 与主稿版本一致。',
        '- **记录边界**：本条只记v50本版修正；v49记录的行号由同一脚本重新核验，首轮报告与v49报告保持不改。',
        '',
    ]
    marker = '### v49\n'
    assert text.count(marker) == 1
    path.write_text(text.replace(marker, '\n'.join(lines) + marker, 1))


def append_companion_record():
    path = ROOT / COMP
    text = path.read_text().rstrip() + '\n'
    start_marker = '## 38. 本版修订（v50）'
    if start_marker in text:
        text = text[:text.index(start_marker)].rstrip() + '\n'
    entries = [
        ('主稿挂起递归源', MAIN, '前置本身挂起时，以它为“对应 T”'),
        ('配套组合行引用', COMP, '| 未归档 + 挂起（任意前置）'),
        ('主稿组合行引用', MAIN, '| 未归档 + 挂起（任意前置）'),
        ('主稿§8.4接手摘要', MAIN, '递归处理该未完成前置（其本身挂起时以其为本段上下文）'),
        ('主稿类型5终归档守卫', MAIN, '最后归档旧任务（已归档者不重复归档）'),
        ('版本同步抬头', COMP, '(./workflow-design.md) v50 同步'),
    ]
    lines = [
        '', '## 38. 本版修订（v50）', '',
        '本文的挂起组合行只引用主设计 §9.1；挂起子任务自身的入口及其返工处理仍在该节递归匹配，不在配套说明复制条件。类型5归档幂等守卫以主设计 §7.7 为唯一源。',
    ]
    for label, file, anchor in entries:
        lines.append(f'- {label} 已同步（{file}:{line_of(file, anchor)}）。')
    lines.append('- 版本 v50；`design: workflow-design.md v50`；与主设计 v50 同版。')
    path.write_text(text + '\n'.join(lines) + '\n')


def generate_fix_notes(rows):
    out = [
        '# v50 修复记录', '',
        '根因、类别扫描与修正判定见 `review-report-v50.md`。清单行号由 `finalize_v50_records.py` 按锚点生成；每个旧/新字符串以 `verify_v50.py` 核验。', '',
        '| ID | 文件 | 落点锚点 | 脚本行号 | 验收位 | 结果 |',
        '|---|---|---|---|---|---|',
    ]
    for row in rows:
        path, anchor = row['文件'], row['锚点']
        if row['锚点'] == 'v50 regression probes':
            loc = line_of(SPEC, '# v50 additions')
        elif row['锚点'] == 'Appendix C v50 insertion':
            loc = line_of(MAIN, '### v50')
        elif row['锚点'] == 'companion §38 v50 insertion':
            loc = line_of(COMP, '## 38. 本版修订（v50）')
        elif row['锚点'] == 'status suffix':
            loc = line_of(MAIN, 'v50 修复：类型 5 终归档调用逐点加守卫')
        elif row['锚点'] == 'Appendix C v49 copy classification':
            loc = line_of(MAIN, '§8.4（M6）为引用式接手摘要')
        else:
            target = row['new'].splitlines()[0]
            # Short anchors avoid treating multiline probe blocks as giant report cells.
            if row['锚点'] == 'guide blind spot 25 paired check':
                loc = line_of(GUIDE, '同一动作全集还须逐调用位配对验收')
            elif row['锚点'] == 'v49 launch probe expected count':
                loc = line_of(SPEC, 'rg -n "开工该未完成前置"')
            elif row['锚点'] == 'probe baseline annotation':
                loc = line_of(SPEC, 'expected scopes as of v50')
            elif row['锚点'] == 'v50 regression probes':
                loc = line_of(SPEC, '# v50 additions')
            else:
                loc = line_of(path, target[:min(len(target), 56)])
        out.append(f"| {row['ID']} | {path} | {anchor} | {path}:{loc} | {row['验收位']} | 已同步 |")
    out += [
        '', '## 脚本生成的版本记录行号', '',
        '附录 C v50 与配套 §38 的所有“已同步”路径和行号由 `finalize_v50_records.py` 生成；`verify_v50.py` 逐条确认目标行内容及章节范围。', '',
        '## 根因 / 修复面', '',
        '- P1/P6：类型5终归档动作全集只有四处，补建与无指向分支有守卫、两个改判分支漏守卫；统一四处分支文案，并以动作调用位而非全篇词频验收。',
        '- P2：前置状态表没有递归展开所下沉对象自身的依赖状态；挂起的前置回到同一第二段表按已有行1–4匹配，阻塞只在递归处理后判定。',
        '- P3：下沉位置由一个扩展到第二段第3行，说明句同步列出两个调用位。',
        '- P4：族2标题同步扩展为建边与返工加边。',
        '- P5：v49记录中的§8.4是被改的接手摘要副本，不是规则源；更正源/副本字段，不改规则正文。',
        '',
    ]
    (REC / 'fix-notes-v50.md').write_text('\n'.join(out))


def main():
    append_main_record()
    append_companion_record()
    append_main_record()
    rows = prepare_manifest()
    generate_fix_notes(rows)
    print(f'manifest rows: {len(rows)}; generated main/companion records and fix-notes')


if __name__ == '__main__':
    main()
