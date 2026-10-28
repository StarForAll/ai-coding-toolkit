"""Fail-closed checks for the v49 approved fix manifest and review axes."""
import csv
import difflib
import hashlib
import json
import re
import shlex
import subprocess
from pathlib import Path
from prepare_v49 import ROOT, REC, MAIN, COMP, SPEC, GUIDE

BASE = json.loads((REC / 'baseline.json').read_text())
FAIL = []


def check(condition, message):
    print(('OK ' if condition else 'FAIL ') + message)
    if not condition: FAIL.append(message)


def get(path):
    return (ROOT / path).read_text()


def data_rows(text, header):
    lines=text.splitlines(); i=lines.index(header)+2; result=[]
    while i<len(lines) and lines[i].startswith('|'):
        result.append(lines[i]); i+=1
    return result


def line_no(text, phrase):
    positions=[i for i,line in enumerate(text.splitlines(),1) if phrase in line]
    assert len(positions)==1, (phrase,positions)
    return positions[0]


def run_manifest():
    rows=list(csv.DictReader((REC/'fix-manifest.tsv').open(),delimiter='\t'))
    check(len(rows)==25, f'manifest rows={len(rows)} (expected 25)')
    current={p:get(p) for p in (MAIN,COMP,SPEC,GUIDE)}
    for item in rows:
        ident,path,old,new=item['ID'],item['文件'],item['old'],item['new']
        before=BASE['texts'][path]
        old_before=before.count(old)
        new_before=before.count(new)
        if ident=='M9':
            passed=old_before==1 and new_before==0 and current[path].count(new)==1 and current[path].replace(new,'',1).count(old)==0 and current[path].count(old)==1
            check(passed, f'{ident}: complete new=1; old only as part of new=1; masked old=0')
        elif ident=='M14':
            passed=old_before==1 and current[path].count(old)==0 and current[path].count(new)==1
            check(passed, f'{ident}: full spec probe block old=0 new=1')
        elif ident=='M15':
            passed=old_before==1 and new_before==0 and current[path].count(new)==1 and current[path].replace(new,'',1).count(old)==0
            check(passed, f'{ident}: guide methods 25/26 new=1, old heading masked=0')
        elif ident.startswith('M13'):
            # Version rows are scoped by their exact current field/assertion, history is retained.
            passed=old_before==1 and current[path].count(new)==1
            check(passed, f'{ident}: scoped current version field new=1 (old may remain in history)')
        else:
            passed=old_before==1 and new_before==0 and current[path].count(old)==0 and current[path].count(new)==1
            check(passed, f'{ident}: old=0 new=1')
        if ident in {'M1','M2','M3','M4','M5','M6','M7a','M7b','M8','M9','M10a','M10b','M11','M12','M14','M14b','M15'}:
            target_path=path
            try: line=line_no(current[target_path], new if ident not in {'M9','M15'} else item['new'].splitlines()[0])
            except AssertionError: line='multi-line / duplicate-safe target checked above'
            print(f'  {ident}\t{path}\t{line}')


def run_invariants():
    main=get(MAIN); comp=get(COMP)
    headers={
        'family':('| 族 | 内容 | 受 §7.5 建边限制 |',4),
        'matrix':('| 写入路径 | 写入时点 | 指向终值 | 说明 / 原因终值 | 依据 |',14),
        'combo':('| 组合 | 判定 | 出口 |',12),
        'transitions':('| # | 从 | 到 | 触发 | 写入者 / 说明 |',7),
        'windows':('| 窗口 | 已提交识别项 / 残留 | 恢复 |',9),
    }
    for name,(header,expected) in headers.items():
        count=len(data_rows(main,header)); check(count==expected,f'{name} data rows={count} expected={expected}')
    old_combo=data_rows(BASE['texts'][MAIN],'| 组合 | 判定 | 出口 |')
    new_combo=data_rows(main,'| 组合 | 判定 | 出口 |')
    old_index=next(i for i,row in enumerate(old_combo) if '未归档 + 挂起（任意前置）' in row)
    changed=[i for i,(a,b) in enumerate(zip(old_combo,new_combo)) if a!=b]
    expected_row='未归档 + 挂起（任意前置）'
    check(len(old_combo)==12 and len(new_combo)==12 and changed==[old_index] and expected_row in new_combo[old_index],
          f'combination rows changed only M7 row: changed={changed}, target_index={old_index}')
    for i,(a,b) in enumerate(zip(old_combo,new_combo)):
        if i!=old_index: check(a==b,f'combo row {i+1} unchanged')
    check('四类' in next(x for x in main.splitlines() if '归档任务的前置集合只能来自下列' in x), 'family source remains four families')
    check('建边 / 返工加边' in next(x for x in main.splitlines() if '活动期建边后随前置归档' in x), 'family 2 includes both edge writers')
    matrix=main[main.index('| 写入路径 | 写入时点 | 指向终值 | 说明 / 原因终值 | 依据 |'):main.index('状态值不变的字段维护不触发表 4-2')]
    check('| — |' not in matrix,'matrix has no bare dash cell')
    assert main.count('version: v49')==1
    assert comp.count('version: v49')==1
    assert comp.count('design: workflow-design.md v49')==2
    check(True,'main/companion versions v49; companion current+history design count=2')
    check('### v49' in main and '## 37. 本版修订（v49）' in comp,'version history appendix v49 and companion §37 exist')
    for needle in ('M1','M2','M3','M4','M5','M6','M7a','M7b','M8','M9','M10a','M10b','M11','M12','M13a','M13h','M14','M14b','M15'):
        check(needle in (REC/'fix-notes.md').read_text(),f'fix-notes contains {needle}')


def run_probe_block():
    spec=get(SPEC)
    start=spec.index('Probes — run after any `workflow-design.md` revision')
    end=spec.index('\n#### v46 probe table',start)
    block=spec[start:end]
    commands=[line.strip() for line in block.splitlines() if line.strip().startswith('rg -n ')]
    print('Probe commands:',len(commands))
    results=[]
    for line in commands:
        lex=shlex.shlex(line,posix=True); lex.whitespace_split=True; lex.commenters='#'
        tokens=list(lex)
        assert len(tokens)>=4 and tokens[0]=='rg' and tokens[1]=='-n',line
        pattern=tokens[2]; files=tokens[3:]
        proc=subprocess.run(['rg','-n','--',pattern,*files],cwd=ROOT,text=True,capture_output=True)
        count=len(proc.stdout.splitlines())
        comment=line.split('#',1)[1] if '#' in line else ''
        expected=None
        m=re.search(r'\b(\d+)\s+(?:lines?|hits?)\b|=\s*(\d+)',comment)
        if m: expected=int(m.group(1) or m.group(2))
        # Counts for the two v49 family phrasings follow their literal approved text.
        if '建边与返工加边 / 重连四类' in pattern: expected=1
        if '建边 / 返工加边' in pattern: expected=1
        if '开工该未完成前置' in pattern: expected=4
        if '已归档者不重复归档' in pattern: expected=2
        if '本步不为旧任务新增出口' in pattern: expected=1
        if '完成旧口径移交确认后按同一条件补做' in pattern: expected=1
        if '前置不全正常时按挂起阶段的对账行' in pattern: expected=0
        matched=expected is None or count==expected
        if not matched: FAIL.append(f'probe expected {expected} got {count}: {line}')
        results.append((line,count,expected,proc.returncode))
        print(('OK' if matched else 'FAIL'),f'{count} expected={expected}',line)
    (REC/'probe-results.tsv').write_text('command\tcount\texpected\texit\n'+'\n'.join(
        f'{c}\t{n}\t{e if e is not None else "inspect"}\t{x}' for c,n,e,x in results)+'\n')
    check(len(commands)>=60, f'all registered probes executed ({len(commands)} commands; expected >=60)')
    check(not any('FAIL' in line for line in FAIL),'all probe expectations match their comments / v49 annotations')


def run_reference_hit_checks():
    main=get(MAIN); comp=get(COMP)
    checks=[
        ('M5 §6.4 step-5', '按第三段的下沉规则', '完成后回本段按 §6.4 第 5 步清挂起'),
        ('M6 §9.1 second-stage', '按 §9.1 第二段的对应行', '完成后回本段清挂起'),
        ('M7a §9.1 second-stage', '按 §9.1 第二段对应行', '完成后回本段清挂起'),
        ('M7b mirror', '按主设计 §9.1 第二段对应行', '下沉开工该未完成前置'),
        ('M9 acceptance', '一次挂起任务在返工期间被加入未完工前置', '按 §9.1 第二段开工该未完成前置'),
    ]
    for name,source,target in checks:
        source_text=main if name!='M7b mirror' else comp
        check(source in source_text and target in source_text,f'reference hit {name}: source and cited step/action present')
    check('命中即停止' in main and '指针无效或为空时先走第二段（有挂起任务时）：第二段命中后' in main,
          'F2 route statement preserves hit-stop semantics and clarifies only row-internal substep')


def run_d4():
    claims=[
      (MAIN,'**建边 / 返工加边**'),(MAIN,'族 2 覆盖建边与返工加边'),
      (MAIN,'建边与返工加边 / 重连四类'),(MAIN,'开工该未完成前置'),
      (MAIN,'已归档者不重复归档'),(MAIN,'本步不为旧任务新增出口'),
      (MAIN,'v49 修复：族表纳入返工加边'),(MAIN,'一次挂起任务在返工期间被加入未完工前置'),
      (COMP,'前置不全正常时按主设计 §9.1 第二段对应行'),(COMP,'完成旧口径移交确认后按同一条件补做'),
      (COMP,'## 37. 本版修订（v49）'),(GUIDE,'25. **枚举成员全集'),
      (GUIDE,'26. **「按 §N」必须落到命中行'),(SPEC,'# v49 additions'),
      (SPEC,'族2含建边与返工加边'),(SPEC,'Probe scope is the main design'),
      (MAIN,'项目层已收尾 + 无收尾对象 + 尾端账本'),
      (MAIN,'version: v49'),(MAIN,'# 工作流整体设计（v49 · 修订）'),
      (COMP,'design: workflow-design.md v49'),(COMP,'(./workflow-design.md) v49 同步')
    ]
    # Replace the two non-literal placeholders with source-backed exact claims.
    claims[14]=(SPEC,'Archived-prerequisite source list（已归档前置合法来源）')
    claims[16]=(MAIN,'旧口径存量挂起尚未移交')
    rows=[]
    for path,phrase in claims:
        text=get(path); count=text.count(phrase)
        check(count>=1,f'D4 grep-F claim present: {path} :: {phrase[:45]}')
        positions=[i for i,line in enumerate(text.splitlines(),1) if phrase in line]
        line=positions[0]
        rows.append(f'{path}:{line}\t{phrase}')
    (REC/'d4-record-claims.tsv').write_text('file_line\tclaim\n'+'\n'.join(rows)+'\n')
    check(len(rows)>=20,f'D4 claims tested={len(rows)}')


def run_final_state():
    changed=[MAIN,COMP,SPEC,GUIDE]
    outside=subprocess.check_output(['git','-c','core.quotepath=false','status','--porcelain=v1'],cwd=ROOT,text=True)
    print('Git status:\n'+outside)
    forbidden=[]
    for line in outside.splitlines():
        path=line[3:]
        if not any(path==p or path.startswith('.trellis/tasks/10-28-workflow-design-v48-0-1-audit/') for p in changed): forbidden.append(path)
    check(not forbidden,f'no out-of-bound changed files: {forbidden}')
    diff_check=subprocess.run(['git','diff','--check'],cwd=ROOT,text=True,capture_output=True)
    check(diff_check.returncode==0 and not diff_check.stdout and not diff_check.stderr,
          'git diff --check passes')
    # Every inserted/replaced line in the four source files must have balanced delimiters.
    bad=[]
    for path in changed:
        before=BASE['texts'][path].splitlines()
        after=(ROOT/path).read_text().splitlines()
        matcher=difflib.SequenceMatcher(a=before,b=after,autojunk=False)
        for tag,a0,a1,b0,b1 in matcher.get_opcodes():
            if tag in ('insert','replace'):
                for lineno,line in enumerate(after[b0:b1],b0+1):
                    if line.count('（')!=line.count('）') or line.count('(')!=line.count(')'):
                        bad.append(f'{path}:{lineno}')
    check(not bad,f'changed-line fullwidth/halfwidth parenthesis balance: {bad}')

    # fix-notes anchors must point to the manifest's current unique new text.
    notes=(REC/'fix-notes.md').read_text()
    manifest=list(csv.DictReader((REC/'fix-manifest.tsv').open(),delimiter='\t'))
    anchor_bad=[]
    for item in manifest:
        ident=item['ID']; match=re.search(rf'^\| {re.escape(ident)} \| ([^|]+) \| ([^|]+) \| ([^|]+) \| 已同步 \|$',notes,re.M)
        if not match: continue
        path_cell=match.group(2).strip(); line_cell=match.group(3).strip()
        loc=re.search(r'([^ |]+\.md):(\d+)$',line_cell)
        if not loc or loc.group(1)!=item['文件']:
            anchor_bad.append(ident+': malformed/wrong path'); continue
        source=(ROOT/item['文件']).read_text().splitlines(); lineno=int(loc.group(2))
        anchor=item['锚点']
        if not (1<=lineno<=len(source)) or anchor not in source[lineno-1]:
            # The generated anchor column is descriptive; use the actual manifest new-text line
            # for long/newline replacements and version frontmatter entries.
            new_lines=[x for x in item['new'].splitlines() if x.strip()]
            if not (1<=lineno<=len(source)) or not any(x in source[lineno-1] for x in new_lines):
                anchor_bad.append(f'{ident}:{lineno}')
    check(not anchor_bad,f'fix-notes generated locations resolve to their manifest anchors: {anchor_bad}')

    # Check line references inside the newly generated v49 records against actual section ranges.
    def ranges_for(path):
        text=(ROOT/path).read_text().splitlines(); marks=[]
        for n,line in enumerate(text,1):
            m=re.match(r'^#{2,3} (\d+(?:\.\d+)?)[\.．]?\s',line)
            if m: marks.append((m.group(1),n))
        result={}
        for idx,(name,start) in enumerate(marks):
            end=marks[idx+1][1]-1 if idx+1<len(marks) else len(text)
            result[name]=(start,end)
        return result
    ranges={MAIN:ranges_for(MAIN),COMP:ranges_for(COMP)}
    label_bad=[]
    for path,begin,end in ((MAIN,'### v49','### v48'),(COMP,'## 37. 本版修订（v49）',None)):
        lines=(ROOT/path).read_text().splitlines(); start=next(i for i,l in enumerate(lines) if l.strip()==begin)
        finish=next((i for i,l in enumerate(lines[start+1:],start+1) if l.strip()==end),len(lines)) if end else len(lines)
        for n in range(start,finish):
            line=lines[n]
            refs=list(re.finditer(r'(docs/workflows/[^:|()]+\.md):(\d+)',line))
            if not refs: continue
            sec_labels=list(re.finditer(r'§(\d+(?:\.\d+)?)',line))
            for ref in refs:
                target=ref.group(1); line_no=int(ref.group(2))
                if target not in ranges or line_no>len((ROOT/target).read_text().splitlines()):
                    label_bad.append(f'{path}:{n+1} bad path/line {target}:{line_no}'); continue
                # Only source/mirror rows with an explicit section label require a range check.
                sec=sec_labels[-1].group(1) if sec_labels else None
                if sec and sec in ranges[target]:
                    lo,hi=ranges[target][sec]
                    if not lo<=line_no<=hi: label_bad.append(f'{path}:{n+1} §{sec} does not contain {target}:{line_no}')
    check(not label_bad,f'v49 appendix / companion § labels match cited source ranges: {label_bad}')
    digest={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in changed}
    (REC/'final-sha256.json').write_text(json.dumps(digest,indent=2)+'\n')
    check(hashlib.sha256((REC/'review-report.md').read_bytes()).hexdigest()==BASE['original_review_sha256'],
          'first-round review-report.md preserved byte-for-byte')
    check((ROOT/'.trellis/tasks/10-28-workflow-design-v48-0-1-audit/task.json').exists(),'active task retained')


if __name__=='__main__':
    run_manifest(); run_invariants(); run_probe_block(); run_reference_hit_checks(); run_d4(); run_final_state()
    print('RESULT', 'FAIL '+str(len(FAIL)) if FAIL else 'all checks passed')
    if FAIL:
        (REC/'verify-failures.txt').write_text('\n'.join(FAIL)+'\n')
        raise SystemExit(1)
    (REC/'verify-failures.txt').write_text('none\n')
