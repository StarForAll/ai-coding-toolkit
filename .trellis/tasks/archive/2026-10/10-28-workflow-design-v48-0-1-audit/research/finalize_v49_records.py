"""Record version edits, residual decisions and generated fix-notes after sources stabilize."""
import csv
import json
from pathlib import Path
from prepare_v49 import ROOT, REC, MAIN, COMP, SPEC, GUIDE
from version_records_v49 import line_of

baseline = json.loads((REC / 'baseline.json').read_text())
main_before, comp_before = baseline['texts'][MAIN], baseline['texts'][COMP]
main_now, comp_now = (ROOT / MAIN).read_text(), (ROOT / COMP).read_text()
main_rows = [
    ('M13a', 'frontmatter version', 'version: v48', 'version: v49', 'v49 version probe / frontmatter'),
    ('M13b', 'title', '# 工作流整体设计（v48 · 修订）', '# 工作流整体设计（v49 · 修订）', 'v49 title probe'),
    ('M13c', '§10 implements_design pin', '模块的 `implements_design` 必须等于本文件 frontmatter 版本（v48）', '模块的 `implements_design` 必须等于本文件 frontmatter 版本（v49）', '§10 current version assertion'),
    ('M13d', '§10 companion design pin', '配套文档的 `design` 字段必须写明本文件版本（`workflow-design.md v48`）', '配套文档的 `design` 字段必须写明本文件版本（`workflow-design.md v49`）', '§10 current version assertion; history excluded'),
]
comp_rows = [
    ('M13f', 'frontmatter version', 'version: v48', 'version: v49', 'v49 version probe / frontmatter'),
    ('M13g', 'frontmatter design field', 'design: workflow-design.md v48\nstatus:', 'design: workflow-design.md v49\nstatus:', 'frontmatter field only; historical §36 pin retained'),
    ('M13h', 'header sync version', '(./workflow-design.md) v48 同步', '(./workflow-design.md) v49 同步', 'header current sync version'),
]

path = REC / 'fix-manifest.tsv'
with path.open() as stream: rows=list(csv.DictReader(stream, delimiter='\t'))
existing={r['ID'] for r in rows}
for ident,label,old,new,acceptance in main_rows+comp_rows:
    if ident in existing: continue
    source=main_before if ident.startswith('M13a') or ident in {'M13b','M13c','M13d','M13e'} else comp_before
    if ident == 'M13d': assert source.count(old)==1
    elif ident == 'M13e': assert source.count(old)==1
    else: assert source.count(old)==1, (ident, source.count(old))
    current=main_now if source is main_before else comp_now
    assert current.count(new)==1, (ident, current.count(new))
    rows.append(dict(ID=ident, 文件=MAIN if source is main_before else COMP,
                     锚点=label, old=old, new=new, 验收位=acceptance,
                     说明='M13 version record; current section only, historical records remain'))
# M13e is the complete frontmatter status line, so the old value has no residual match.
if 'M13e' not in existing:
    old_status = next(line for line in main_before.splitlines() if line.startswith('status:'))
    new_status = next(line for line in main_now.splitlines() if line.startswith('status:'))
    rows.append(dict(ID='M13e', 文件=MAIN, 锚点='frontmatter status', old=old_status, new=new_status,
                     验收位='v49 status note; version assertion', 说明='complete status line replaced; full old line must be absent'))
with path.open('w') as stream:
    writer=csv.DictWriter(stream, fieldnames=['ID','文件','锚点','old','new','验收位','说明'], delimiter='\t')
    writer.writeheader(); writer.writerows(rows)

def anchor_line(path, anchor, occurrence=1):
    return line_of(path, anchor, occurrence)

source_map = {
 'M1': (MAIN, '| **活动期建边后随前置归档** | **建边 / 返工加边**'),
 'M2': (MAIN, '族 2 覆盖建边与返工加边'),
 'M3': (MAIN, '产生路径族括号：任务定义（创建期写 deps / 收尾重定义）'),
 'M4': (MAIN, '任务定义 / 继承 / 建边与返工加边 / 重连四类'),
 'M5': (MAIN, '按第三段的下沉规则先开工该未完成前置'),
 'M6': (MAIN, '按 §9.1 第二段的对应行先开工该未完成前置'),
 'M7a': (MAIN, '前置不全正常时按 §9.1 第二段对应行开工该未完成前置'),
 'M7b': (COMP, '前置不全正常时按主设计 §9.1 第二段对应行'),
 'M8': (MAIN, '指针无效或为空时先走第二段（有挂起任务时）：'),
 'M9': (MAIN, '一次挂起任务在返工期间被加入未完工前置'),
 'M10a': (MAIN, '已归档者不重复归档', 1),
 'M10b': (MAIN, '已归档者不重复归档', 2),
 'M11': (MAIN, '本步不为旧任务新增出口'),
 'M12': (COMP, '完成旧口径移交确认后按同一条件补做'),
 'M14': (SPEC, '# v49 additions'),
 'M14b': (SPEC, 'Archived-prerequisite source list（已归档前置合法来源）'),
 'M15': (GUIDE, '25. **枚举成员全集'),
 'M13a': (MAIN, 'version: v49'),
 'M13b': (MAIN, '# 工作流整体设计（v49 · 修订）'),
 'M13c': (MAIN, 'implements_design` 必须等于本文件 frontmatter 版本（v49）'),
 'M13d': (MAIN, '配套文档的 `design` 字段必须写明本文件版本（`workflow-design.md v49`）'),
 'M13e': (MAIN, 'v49 修复：族表纳入返工加边'),
 'M13f': (COMP, 'version: v49'),
 'M13g': (COMP, 'design: workflow-design.md v49'),
 'M13h': (COMP, '(./workflow-design.md) v49 同步'),
}

notes=[]
notes += ['# v49 修复记录', '',
          '基于第二轮扫描及已批准的 M1–M15 清单。old/new 落点与 `已同步` 后的行号由本脚本按唯一文本锚点生成；修改后若行号变化，重新运行本脚本。', '',
          '## 根因与范围', '',
          '- F1 根因：成员全集没有同一动作全集交叉表；“建边”收窄后，没有复核返工加边写者，调用位/probe 只保证短语存在。M1/M2/M3/M4修源与两处枚举；Guide 25要求先出全集矩阵。',
          '- F2 根因：以引用章节名代替命中类型/行的前提检查；“按§7.7对账”在挂起合法等待态没有任何类型输入可匹配，并与“命中即停止”说明冲突。M5–M9补具体下沉动作、同状态镜像与验收。',
          '- P2/P3/P4 根因及处理：类型5借用归档动作未写归档态幂等性；局部两出口表述使用全局“只有”；配套场景投影遗漏移交守卫。分别由M10、M11、M12限定。', '',
          '## 修复清单及脚本行号', '', '| ID | 源 / 镜像 | § / 锚点 | 脚本位置 | 处理 |', '|---|---|---|---|---|']
for item in rows:
    ident=item['ID']
    if ident not in source_map: continue
    source=source_map[ident]
    p,anchor=source[0],source[1]
    occurrence=source[2] if len(source)>2 else 1
    line=anchor_line(p,anchor,occurrence)
    notes.append(f"| {ident} | {item['文件']} | {item['锚点']} | {p}:{line} | 已同步 |")
notes += ['', '## 验收位', '',
          '- M1/M2：族2 source cell 与唯一注记；M3/M4：两份路径族枚举；M14/M14b：注册探针及来源注册表。',
          '- M5/M6/M7a/M7b/M9：状态入口、接手摘要、组合表、配套镜像和连续自检；新增场景在正文 §10。',
          '- M10a/M10b：两处类型5动作的幂等限定和 probe；M11：probe；M12：配套场景行及probe。',
          '- M15：guide盲点25/26；本报告D1–D5和实际运行probe为方法执行记录。',
          '- M13：版本三元一致性；附录C与配套§37的逐项引用行号由 `version_records_v49.py` 生成。', '',
          '## 未同步项', '', '无。所有“已同步”位点均有上述唯一锚点及脚本产出行号；附录C / 配套§37使用相同生成脚本。', '']
(REC / 'fix-notes.md').write_text('\n'.join(notes))

residuals = '''# v49 residuals

| 项 | 触发 / 观察 | 决定 | 去向 |
|---|---|---|---|
| R1 | 执行前清单预期 HEAD=870d9d7；实际为 a82a54f，二者目标四源 diff 为空 | 留作环境事实；按当前 HEAD 执行，未改历史 | review-report-v2.md 基线段 |
| R2 | M14 指定要改写的 `rg -n "建边 / 重连四类"` 不在 `.trellis/spec/docs/index.md`，只在归档 verifier 的注释中；边界不允许改归档文件 | 不改边界外文件；在spec新增等价族 probe。全短语的准确定稿 new 只出现1次，较宽路径族片语出现2次，因此分别断言1/2 | probe 注释与 verify_v49.py；需独立留意不把不存在的旧探针谎报为已修改 |
| R3 | M9 固定 new 保留 old 片语，故全局 old==0 与 new==1矛盾 | 不改定稿；校验完整 new 恰一处、屏蔽new后old==0、全局old==1 | verify_v49.py 对 M9 使用特例 |
| R4 | 扫描到其它按§7.7完整性分类/对账引用，但输入映射到既有类型1–5、合法等待、正常状态复判或明确报告阻塞 | 不扩大发现、不新增机制；逐条目标写入 S2 TSV | review-report-v2.md S2 |
| R5 | S3 的“全正常+未结束R”按§6.4挂载守卫不可达；“前置含已归档正常”可与其它未完成前置并存 | 表中注明不可达/组合拆解，不制造空格或新路由 | review-report-v2.md S3 |

无其它清单外发现；D1–D5按指定验收轴执行，不声明全域无残留。
'''
(REC / 'residuals.md').write_text(residuals)
print('fix-notes lines', len((REC/'fix-notes.md').read_text().splitlines()), 'manifest rows', len(rows))
