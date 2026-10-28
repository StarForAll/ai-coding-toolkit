"""Apply only the frozen v49 manifest, in the authorized phase order."""
import csv
import hashlib
import json
import sys
from pathlib import Path
from prepare_v49 import ROOT, REC, MAIN, COMP, SPEC, GUIDE
from scan_v49 import extract


def load_rows():
    with (REC / 'fix-manifest.tsv').open() as stream:
        return list(csv.DictReader(stream, delimiter='\t'))


def save_rows(rows):
    with (REC / 'fix-manifest.tsv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=['ID', '文件', '锚点', 'old', 'new', '验收位', '说明'], delimiter='\t')
        writer.writeheader(); writer.writerows(rows)


def apply(rows, identifiers):
    for ident in identifiers:
        item = next(row for row in rows if row['ID'] == ident)
        path = ROOT / item['文件']
        text = path.read_text()
        assert text.count(item['old']) == 1, (ident, 'old count', text.count(item['old']))
        assert text.count(item['new']) == 0, (ident, 'new already exists')
        text = text.replace(item['old'], item['new'], 1)
        assert text.count(item['new']) == 1
        assert text.replace(item['new'], '', 1).count(item['old']) == 0
        path.write_text(text)
        line = text[:text.index(item['new'])].count('\n') + 1
        print(ident, item['文件'], line, 'old-outside-new=0', 'new=1')


def core():
    baseline = json.loads((REC / 'baseline.json').read_text())
    for path, sha in baseline['sha256'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == sha, path
    report_path = REC / 'review-report-v2.md'
    report = report_path.read_text()
    assert all(title in report for title in ('## S1', '## S2', '## S3', '## 反驳门'))
    hits = extract(baseline['texts'])
    table = ['### S2 逐项命中明细（脚本抽取、人工校正目标）', '', '| 位点 | 引用 | 目标命中 |', '|---|---|---|']
    for hit in hits:
        table.append(f"| {hit['文件']}:{hit['行']} | {hit['引用']} | {hit['命中']} |")
    report = report.replace('## S3 ', '\n'.join(table) + '\n\n## S3 ', 1)
    report_path.write_text(report)
    (REC / 'scan-gate.json').write_text(json.dumps({
        'pre_edit_report_sha256': hashlib.sha256(report.encode()).hexdigest(),
        'reference_count': len(hits), 'source_sha256_before_edit': baseline['sha256'],
    }, ensure_ascii=False, indent=2) + '\n')
    rows = load_rows()
    apply(rows, ['M1', 'M2', 'M5', 'M8', 'M10a', 'M10b', 'M11'])
    apply(rows, ['M3', 'M4', 'M6', 'M7a', 'M7b', 'M9', 'M12'])


METHODS = '''25. **枚举成员全集 vs 调用位清单。** 改一个"覆盖若干动作 / 若干族 / 若干行"的枚举时，列"调用位"不够——必须列出被枚举对象的**全集**并逐项打勾。v48 把 §4.4 族 2 收窄成「建边」以分出重连族，同一份 fix-notes 已经把「返工加边」写进论证，却没有把它带进族表与路径族两处枚举，于是 0→1 返工的正常产出态（被返工任务 T 归档、前置含已归档 R）掉到四族之外，并从 v48 活到下一次审查。规则：改枚举先出全集表；清单缺项即失败。
26. **「按 §N」必须落到命中行。** 任何"按 §N 对账 / 按 §N 处置"都要指出目标段里命中的**具体类型 / 表行 / 步骤号**；命中不到，要么改措辞，要么承认缺口。"有入口、有出口"按名字核对不算通过——§9.1 第二段「按 §7.7 对账」在 v30–v48 的每一轮里都被当作出口读过去，实际 §7.7 的五类无一匹配。
'''


def instrument():
    rows = load_rows()
    spec = (ROOT / SPEC).read_text()
    start = spec.index('Probes — run after any `workflow-design.md` revision')
    end = spec.index('\n#### v46 probe table', start)
    old_block = spec[start:end]
    new_block = old_block.replace('expected scopes as of v48', 'expected scopes as of v49', 1)
    note = ('v49 adds six regression probes plus the family-enumeration command that was\n'
            'absent from the v48 spec block, and one supplemental scope-disambiguation\n'
            'probe. The full four-family phrase occurs once; the broader two-enumeration\n'
            'phrase occurs twice, because the first enumeration has no 四类 suffix.\n\n')
    new_block = new_block.replace('Probe scope is the main design', note + 'Probe scope is the main design', 1)
    additions = r'''# v49 additions (scope = the two design documents only; no task-path dependency):
rg -n "建边与返工加边 / 重连四类" docs/workflows/workflow-design.md   # 1 hit: only the second enumeration has 四类; the first ends after 重连
rg -n "建边与返工加边 / 重连" docs/workflows/workflow-design.md   # 2 hits: both path-family enumerations; one includes 四类 and one does not
rg -n "\*\*建边 / 返工加边\*\*" docs/workflows/workflow-design.md   # 1 hit: family-2 source cell
rg -n "开工该未完成前置" docs/workflows/workflow-design.md   # 4 hits: hanging-route row, handoff mirror, combination-row exit and self-check
rg -n "已归档者不重复归档" docs/workflows/workflow-design.md   # 2 hits: type-5 build and no-pointer branches
rg -n "本步不为旧任务新增出口" docs/workflows/workflow-design.md   # 1 hit: baseline-change local-scope sentence
rg -n "完成旧口径移交确认后按同一条件补做" docs/workflows/依赖机制设计说明.md   # 1 hit: scenario-table handoff prerequisite
rg -n "前置不全正常时按挂起阶段的对账行" docs/workflows/workflow-design.md docs/workflows/依赖机制设计说明.md   # 0 hits: obsolete hanging-reconciliation exit
'''
    new_block = new_block.rsplit('```', 1)[0] + additions + '```\n'
    rows.append(dict(ID='M14', 文件=SPEC, 锚点='Predicate Registry and Probes 的探针块',
                     old=old_block, new=new_block, 验收位='全量按spec实际运行；D5',
                     说明='旧族探针不在spec；新增七条命令，完整族短语期望纠正为1；正文定稿不改'))
    old = '\n## Known False-Positive Patterns In This Repo'
    rows.append(dict(ID='M15', 文件=GUIDE, 锚点='blind spots末尾', old=old,
                     new='\n' + METHODS + old, 验收位='guide条目25/26逐字核对；D1/D2本版执行记录',
                     说明='方法义务只写guide；new保留下一章节锚点'))
    save_rows(rows)
    apply(rows, ['M14', 'M15'])


if __name__ == '__main__':
    {'core': core, 'instrument': instrument}[sys.argv[1]]()
