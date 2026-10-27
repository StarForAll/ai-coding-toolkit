import csv, sys
from pathlib import Path
ROOT = Path("/home/xzc/projects/personal/ai-coding-toolkit")
REC = Path(__file__).resolve().parent
MAN = REC / "fix-manifest-r3.tsv"
FILES = {
    "主稿": ROOT / "docs/workflows/workflow-design.md",
    "配套": ROOT / "docs/workflows/依赖机制设计说明.md",
    "spec": ROOT / ".trellis/spec/docs/index.md",
    "residuals": REC / "residuals.md",
}
texts = {k: p.read_text(encoding="utf-8") for k, p in FILES.items()}
rows = list(csv.DictReader(MAN.open(encoding="utf-8"), delimiter="\t"))
errors = []
for r in rows:
    rid = r["ID"]; key = r["文件"]
    old = r["旧文"].replace("\\n", "\n")
    new = r["新文"].replace("\\n", "\n")
    t = texts[key]
    n = t.count(old)
    expect = 2 if rid == "R8b" else 1
    if n != expect:
        errors.append(f"{rid}: old count {n} != {expect}")
        continue
    texts[key] = t.replace(old, new, expect)
if errors:
    print("\n".join(errors)); sys.exit(1)
for k, p in FILES.items():
    p.write_text(texts[k], encoding="utf-8")
print("applied", len(rows), "rows")
