import hashlib
import json
import subprocess
import re
from pathlib import Path

ROOT=Path('/home/xzc/projects/personal/ai-coding-toolkit')
REC=ROOT/'.trellis/tasks/10-28-workflow-design-v48-0-1-audit/research'
FILES=['docs/workflows/workflow-design.md','docs/workflows/依赖机制设计说明.md',
       '.trellis/spec/docs/index.md','.trellis/spec/guides/design-review-thinking-guide.md']
MAIN=(ROOT/FILES[0]).read_text()
lines=MAIN.splitlines()
start=next(i for i,l in enumerate(lines) if '**替换/放弃未完成**' in l)
end=next(i for i,l in enumerate(lines[start+1:],start+1) if l.startswith('- **“正常”的写入者**'))
calls=[]
for n,line in enumerate(lines[start:end],start+1):
    for m in re.finditer(r'最后归档旧任务|补齐下游删边与旧任务归档',line):
        left=max(line.rfind('；',0,m.start()),line.rfind(';',0,m.start()),-1)+1
        stops=[x for x in (line.find('；',m.end()),line.find(';',m.end()),line.find('。',m.end())) if x>=0]
        right=min(stops) if stops else len(line)
        clause=line[left:right]
        calls.append({'line':n,'call':m.group(),'guard':'不重复归档' in clause,'clause':clause})
snapshot={
 'git_status':subprocess.check_output(['git','-c','core.quotepath=false','status','--porcelain=v1'],cwd=ROOT,text=True),
 'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 'sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FILES},
 'versions':{'main':'v49','companion':'v49'},
 'archive_action_call_count':len(calls),
 'archive_action_guarded_count':sum(c['guard'] for c in calls),
 'archive_actions':calls,
 'review_v1_sha256':hashlib.sha256((REC/'review-report.md').read_bytes()).hexdigest(),
 'review_v2_sha256':hashlib.sha256((REC/'review-report-v2.md').read_bytes()).hexdigest(),
}
assert len(calls)==4 and snapshot['archive_action_guarded_count']==2, calls
(REC/'followup-v50-baseline.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in snapshot.items() if k not in ('archive_actions',)},ensure_ascii=False,indent=2))
