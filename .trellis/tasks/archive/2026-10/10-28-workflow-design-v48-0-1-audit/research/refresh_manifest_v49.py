import csv, json
from pathlib import Path
from prepare_v49 import ROOT, REC, SPEC

baseline=json.loads((REC/'baseline.json').read_text())
before=baseline['texts'][SPEC]
after=(ROOT/SPEC).read_text()
start_marker='Probes — run after any `workflow-design.md` revision'
end_marker='\n#### v46 probe table'
def extract(text):
    a=text.index(start_marker); b=text.index(end_marker,a)
    return text[a:b]
old,new=extract(before),extract(after)
assert before.count(old)==1 and after.count(new)==1
path=REC/'fix-manifest.tsv'
with path.open() as stream: rows=list(csv.DictReader(stream,delimiter='\t'))
item=next(r for r in rows if r['ID']=='M14')
item['old']=old; item['new']=new
with path.open('w') as stream:
    writer=csv.DictWriter(stream,fieldnames=['ID','文件','锚点','old','new','验收位','说明'],delimiter='\t')
    writer.writeheader();writer.writerows(rows)
print('M14 manifest refreshed from frozen baseline and final spec block')
