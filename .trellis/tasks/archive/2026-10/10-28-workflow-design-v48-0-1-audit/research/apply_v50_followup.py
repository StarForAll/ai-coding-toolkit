"""Apply the approved v50 follow-up across the in-scope source documents."""
import csv
import re
from pathlib import Path

ROOT = Path('/home/xzc/projects/personal/ai-coding-toolkit')
REC = ROOT / '.trellis/tasks/10-28-workflow-design-v48-0-1-audit/research'
MAIN = 'docs/workflows/workflow-design.md'
COMP = 'docs/workflows/依赖机制设计说明.md'
SPEC = '.trellis/spec/docs/index.md'
GUIDE = '.trellis/spec/guides/design-review-thinking-guide.md'
edits = []


def add(ident, path, anchor, old, new, acceptance, reason):
    edits.append(dict(ID=ident, 文件=path, 锚点=anchor, old=old, new=new,
                      验收位=acceptance, 说明=reason))


# Version and status pins.
add('V50-11', MAIN, 'frontmatter version', 'version: v49', 'version: v50', '两文档版本同为v50', 'M13')
add('V50-12', MAIN, 'main title', '# 工作流整体设计（v49 · 修订）', '# 工作流整体设计（v50 · 修订）', '标题与frontmatter同版', 'M13')
add('V50-13', MAIN, 'status suffix', '；v49 修复：族表纳入返工加边、挂起子态补向前动作、路径族与类型 5 归档条件化、配套移交门', '；v49 修复：族表纳入返工加边、挂起子态补向前动作、路径族与类型 5 归档条件化、配套移交门；v50 修复：类型 5 终归档调用逐点加守卫、挂起前置递归匹配本段、族 2 标题与成员对齐、修订记录源副本归类更正', 'status含v50修订摘要', 'M13')
add('V50-14', MAIN, '§10 implements_design pin', '模块的 `implements_design` 必须等于本文件 frontmatter 版本（v49）', '模块的 `implements_design` 必须等于本文件 frontmatter 版本（v50）', '版本引用探针；§标签范围核验', 'M13')
add('V50-15', MAIN, '§10 companion design pin', '配套文档的 `design` 字段必须写明本文件版本（`workflow-design.md v49`）', '配套文档的 `design` 字段必须写明本文件版本（`workflow-design.md v50`）', '版本引用探针；§标签范围核验', 'M13')
add('V50-16', COMP, 'companion frontmatter version', 'version: v49', 'version: v50', '两文档版本同为v50', 'M13')
add('V50-17', COMP, 'companion design pin', 'design: workflow-design.md v49\nstatus: 设计层说明', 'design: workflow-design.md v50\nstatus: 设计层说明', '两文档design pin一致', 'M13')
add('V50-18', COMP, 'companion sync header', 'v49 同步；状态表', 'v50 同步；状态表', '抬头与frontmatter同版', 'M13')

# Correct the v49 source/copy classification without changing its normative content.
add('V50-19', MAIN, 'Appendix C v49 source classification', '§9.1第二段（M5）、§8.4（M6）、§7.7组合表（M7a）', '§9.1第二段（M5，唯一规则源）、§7.7组合表（M7a）', 'D4源/副本登记回查；旧源短语=0', 'P5')
add('V50-20', MAIN, 'Appendix C v49 copy classification', 'M7a由配套 §8 组合表行（M7b）镜像；', '§8.4（M6）为引用式接手摘要；M7a由配套 §8 组合表行（M7b）镜像；', 'D4源/副本登记回查；§8.4引用式=1', 'P5')

# Keep the route mirrors as references to the single §9.1 source.
add('V50-21', MAIN, '§7.7 hanging combination row',
    '| 未归档 + 挂起（任意前置） | 合法（等待返工） | §6.4 评估 / 进入 R；前置不全正常时按 §9.1 第二段对应行开工该未完成前置，完成后回本段清挂起 |',
    '| 未归档 + 挂起（任意前置） | 合法（等待返工） | §6.4 评估 / 进入 R；前置不全正常时按 §9.1 第二段对应行递归处理该未完成前置（其本身挂起时回本段重新匹配），完成后回本段清挂起 |',
    '主稿挂起组合表镜像引用probe=1','P2;引用源递归情形')
add('V50-22', COMP, 'companion §8 hanging combination row',
    '| 未归档 + 挂起（任意前置） | 合法（等待返工） | 主设计 §6.4 评估 / 进入 R；前置不全正常时按主设计 §9.1 第二段对应行（下沉开工该未完成前置） |',
    '| 未归档 + 挂起（任意前置） | 合法（等待返工） | 主设计 §6.4 评估 / 进入 R；前置不全正常时按主设计 §9.1 第二段对应行递归处理该未完成前置（其本身挂起时以其为本段上下文） |',
    '配套挂起组合表镜像引用probe=1','P2;配套保持引用式')

# Probe block updates: as-of version and every new regression assertion.
add('V50-23', SPEC, 'probe baseline annotation', 'expected scopes as of v49', 'expected scopes as of v50', '全文版本基准注= v50', 'M14')
add('V50-24', SPEC, 'v49 launch probe expected count', 'rg -n "开工该未完成前置" docs/workflows/workflow-design.md   # 4 hits: hanging-route row, handoff mirror, combination-row exit and self-check', 'rg -n "开工该未完成前置" docs/workflows/workflow-design.md   # 1 hit as of v50: the ordinary-predecessor branch; the recursive self-check starts with Q already suspended', 'v50全量探针实际=1', 'P2;旧命中计数随镜像改写')
add('V50-25', SPEC, 'v50 regression probes', '```\n\n#### v46 probe table', '''# v50 additions (scope = the two design documents only; per-action checks are anchored to type-5 branches):
rg -n "活动期建边 / 返工加边后随前置归档" docs/workflows/workflow-design.md   # 1 hit: family-2 title matches both members
rg -n "活动期建边后随前置归档" docs/workflows/workflow-design.md   # 0 hits: obsolete narrow family-2 title
rg -n '最后归档旧任务（已归档者不重复归档）|补齐下游删边与旧任务归档（已归档者不重复归档）' docs/workflows/workflow-design.md   # 3 matching lines contain four type-5 sites; verify branch identity in the script
rg -o "已归档者不重复归档" docs/workflows/workflow-design.md   # 5 occurrences: four type-5 guards plus the type-1 counterpart
rg -n "旧任务已归档，不重复归档" docs/workflows/workflow-design.md   # 0 hits: inconsistent guard wording removed
rg -n "前置本身挂起时，以它为“对应 T”回到本段并完整匹配本表" docs/workflows/workflow-design.md   # 1 hit: §9.1 second-stage row 3 re-enters the full table
rg -n "R 自身挂起时以 R 为“对应 T”回到本段并匹配各行" docs/workflows/workflow-design.md   # 1 hit: §9.1 second-stage row 1 recursively handles a suspended rework task
rg -n "递归处理该未完成前置（其本身挂起时以其为本段上下文）" docs/workflows/workflow-design.md "docs/workflows/依赖机制设计说明.md"   # 2 hits: §8.4 and companion §8 remain references to the main route
rg -n "下沉是『当前任务』行与第二段第 3 行内的分支" docs/workflows/workflow-design.md   # 1 hit: explanation covers both downshift sites
rg -n "下沉是『当前任务』行内的分支" docs/workflows/workflow-design.md   # 0 hits: stale explanation removed
rg -n "Q 自身挂起且有未归档 R_Q" docs/workflows/workflow-design.md   # 1 hit: §10 self-check exercises the recursive route
rg -n "§9.1第二段（M5，唯一规则源）" docs/workflows/workflow-design.md   # 1 hit: corrected v49 source record
rg -n "§8.4（M6）为引用式接手摘要" docs/workflows/workflow-design.md   # 1 hit: corrected v49 copy record
rg -n "§9.1第二段（M5）、§8.4（M6）" docs/workflows/workflow-design.md   # 0 hits: obsolete source/copy classification removed
rg -n "同一动作全集还须逐调用位配对验收" ".trellis/spec/guides/design-review-thinking-guide.md"   # 1 hit: guide 25 contains a mechanical per-call-site example

```

#### v46 probe table''', '每条probe逐项全量比对注释', 'M14')

# Method obligation 25 receives a concrete paired-acceptance example, not a new rule.
old_guide25 = '25. **枚举成员全集 vs 调用位清单。** 改一个"覆盖若干动作 / 若干族 / 若干行"的枚举时，列"调用位"不够——必须列出被枚举对象的**全集**并逐项打勾。v48 把 §4.4 族 2 收窄成「建边」以分出重连族，同一份 fix-notes 已经把「返工加边」写进论证，却没有把它带进族表与路径族两处枚举，于是 0→1 返工的正常产出态（被返工任务 T 归档、前置含已归档 R）掉到四族之外，并从 v48 活到下一次审查。规则：改枚举先出全集表；清单缺项即失败。\n'
new_guide25 = '25. **枚举成员全集 vs 调用位清单。** 改一个"覆盖若干动作 / 若干族 / 若干行"的枚举时，列"调用位"不够——必须列出被枚举对象的**全集**并逐项打勾。v48 把 §4.4 族 2 收窄成「建边」以分出重连族，同一份 fix-notes 已经把「返工加边」写进论证，却没有把它带进族表与路径族两处枚举，于是 0→1 返工的正常产出态（被返工任务 T 归档、前置含已归档 R）掉到四族之外，并从 v48 活到下一次审查。规则：改枚举先出全集表；清单缺项即失败。同一动作全集还须逐调用位配对验收，不能只做总词频比较：例如类型 5 四个终归档分支都必须有“已归档者不重复归档”守卫；脚本逐分支核对补建、一般任务改判放弃、P 改判放弃、无指向四个位点，不能只比“归档”与“守卫”的全篇计数。\n'
add('V50-26', GUIDE, 'guide blind spot 25 paired check',
    old_guide25,
    new_guide25,
    'guide probe + verifier四分支断言','P1/P6 method example')


def replace_once(text, item):
    old, new = item['old'], item['new']
    count = text.count(old)
    if item['ID'] == 'V50-26' and count == 0 and text.count(new) == 1:
        return text
    if count != 1:
        raise AssertionError((item['ID'], item['文件'], 'old-count', count, old[:90]))
    if new and text.count(new):
        raise AssertionError((item['ID'], item['文件'], 'new-exists', text.count(new), new[:90]))
    return text.replace(old, new, 1)


def main():
    paths = sorted({item['文件'] for item in edits})
    buffers = {path: (ROOT / path).read_text() for path in paths}
    for item in edits:
        buffers[item['文件']] = replace_once(buffers[item['文件']], item)
    for path, text in buffers.items():
        (ROOT / path).write_text(text)
    with (REC / 'fix-manifest-v50.tsv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=['ID','文件','锚点','old','new','验收位','说明'], delimiter='\t')
        writer.writeheader()
        writer.writerows(edits)
    print(f'applied {len(edits)} v50 follow-up edits across {len(paths)} in-scope files')


if __name__ == '__main__':
    main()
