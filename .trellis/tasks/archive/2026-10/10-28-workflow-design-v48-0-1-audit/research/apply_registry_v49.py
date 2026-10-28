import csv
from pathlib import Path
from prepare_v49 import ROOT, REC, SPEC

old = '| Archived-prerequisite source list（已归档前置合法来源） | 主设计 §4.4 归档终态约束（四族表） | “来源按 §4.4 判定”“按 §4.4 四族”“（含任务定义类，术语见 §3）”; companion: “按主设计 §4.4 判定”“来源按主设计 §4.4” | Restating the member enumeration (including the family-2 clause) in §7.5 / §0 / companion; a second producer list |'
new = '| Archived-prerequisite source list（已归档前置合法来源） | 主设计 §4.4 归档终态约束（四族表；族2含建边与返工加边） | “来源按 §4.4 判定”“按 §4.4 四族”“（含任务定义类，术语见 §3）”; companion: “按主设计 §4.4 判定”“来源按主设计 §4.4” | Restating the member enumeration (including family 2’s edge/rework-edge members) in §7.5 / §0 / companion; a second producer list or treating the iteration-edge guard as the rework-edge guard |'
path = ROOT / SPEC
text = path.read_text()
assert text.count(old) == 1
assert text.count(new) == 0
path.write_text(text.replace(old, new, 1))
manifest = REC / 'fix-manifest.tsv'
with manifest.open() as stream: rows=list(csv.DictReader(stream, delimiter='\t'))
rows.append(dict(ID='M14b', 文件=SPEC, 锚点='Predicate Registry：Archived-prerequisite source list', old=old, new=new,
                 验收位='族2 source member and guard domain accurately registered; D1',
                 说明='Registry follows sole-source §4.4; iteration-edge restriction is not copied onto rework-add-edge'))
with manifest.open('w') as stream:
    writer=csv.DictWriter(stream, fieldnames=['ID','文件','锚点','old','new','验收位','说明'], delimiter='\t')
    writer.writeheader(); writer.writerows(rows)
print('M14b', SPEC, 'old=1 new=1')
