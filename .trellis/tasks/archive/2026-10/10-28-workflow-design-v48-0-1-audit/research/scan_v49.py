"""Enumerate exact reference clauses from frozen or current local documents."""
import csv
import json
import re
from pathlib import Path
from prepare_v49 import ROOT, REC, MAIN, COMP

RX = re.compile(r'按\s*(?:主设计\s*)?§\d+(?:\.\d+)?(?:(?!按\s*(?:主设计\s*)?§)[^；。\n|]){0,160}?(?:对账|处置)')


def extract(texts):
    hits = []
    for path in (MAIN, COMP):
        history = False
        section = 'frontmatter / 概览'
        for num, line in enumerate(texts[path].splitlines(), 1):
            if line.startswith('#'):
                section = line
            if line.startswith('## 附录') or line.startswith('## 14.'):
                history = True
            for match in RX.finditer(line):
                domain = '历史/概览/审查标准' if history or (path == MAIN and num < 102) else '规范'
                clause = match.group()
                if domain != '规范':
                    target = '记录或审查用例；非当前执行入口'
                elif path == MAIN and num == 373 and '§6.4' in clause:
                    target = '主稿 §6.4 登记/执行/清挂起步骤1–5，或 §6.6 放弃实施步骤1–5；均先各自守卫'
                elif (path == MAIN and num == 494) or (path == COMP and num == 184):
                    target = '主稿 §6.6 实施第2步删边，或 §6.5 实施第2–3步继承/重连；已有异常处分经§7.4→类型5，不重新发起已归档对象'
                elif path == MAIN and num == 837:
                    target = '§3 当前任务无效条款 → §9.1 无当前任务分支；正常未归档明确由§7.7类型3人发起修复'
                elif path == MAIN and num == 827:
                    target = '§7.7 组合表行10/11等待、尾行重定义；字段非法类型4、前置正常未归档类型3、归档未记账类型1；普通无就绪合法等待不伪造修复类型'
                elif path == MAIN and num == 911:
                    target = '§0.1口径10②人工执行扫描义务；这是自检用例的审查动作，不是任务对账入口'
                elif '§7.4' in clause:
                    target = '主稿 §7.4 异常表行 → 处分终态，或类型5；字段/角色不一致先类型4'
                elif '类型 3' in clause:
                    target = '主稿 §7.7 类型3（配套 §8 类型3）'
                elif '类型 5' in clause:
                    target = '主稿 §7.7 类型5（配套 §8 类型5）'
                elif '类型 2' in clause:
                    target = '主稿 §7.7 类型2（配套 §8 类型2）'
                elif '组合表行 2' in clause:
                    target = '主稿 §7.7 组合表行2 → 类型4'
                elif '等待' in clause:
                    target = '主稿 §7.7 组合表行10/11（配套 §8 同行）；前置异常→§7.4，正常未归档→类型3'
                elif path == MAIN and num in (775, 802):
                    target = 'F2：无匹配类型；挂起+R已归档+Q未完工是合法等待；由M5/M6改为下沉开工Q'
                elif '计入对账' in clause:
                    target = '主稿 §7.7 类型4（记录无法解析）'
                elif '补记' in line:
                    target = '主稿 §7.7 类型1（卸载期间归档，重装后补记）'
                elif '重装' in line or '重装' in clause:
                    target = '主稿 §7.7 分类守卫与类型1–5；逐项按实际组合命中，不要求所有项同属一种'
                elif '旧任务已归档' in line or '收尾' in line or '持久化失败' in line or '失败' in line:
                    target = '归档已完成但正常未提交→类型1；归档前失败且事实未变→原组合，非虚构修复类型'
                elif '异常' in line:
                    target = '字段/角色损坏→类型4；合法未完成异常处分→类型5；按§7.4终态复判'
                else:
                    target = '人工逐条核对目标章节的具体动作（见v2报告S2补充说明）'
                hits.append(dict(文件=path, 行=num, 章节=section, 域=domain, 引用=clause, 命中=target))
    return hits


if __name__ == '__main__':
    texts = json.loads((REC / 'baseline.json').read_text())['texts']
    hits = extract(texts)
    with (REC / 's2-references-before.tsv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(hits[0]), delimiter='\t')
        writer.writeheader(); writer.writerows(hits)
    for hit in hits:
        if hit['域'] == '规范':
            print(f"{hit['文件']}:{hit['行']} | {hit['引用']} | {hit['命中']}")
    print('规范引用', sum(h['域'] == '规范' for h in hits), '历史/标准', sum(h['域'] != '规范' for h in hits))
