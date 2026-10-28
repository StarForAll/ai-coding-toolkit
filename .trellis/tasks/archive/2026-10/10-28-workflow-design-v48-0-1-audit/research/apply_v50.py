"""Apply follow-up v50 changes after the complete class scan is recorded."""
import csv
import hashlib
import json
from pathlib import Path

ROOT=Path('/home/xzc/projects/personal/ai-coding-toolkit')
REC=ROOT/'.trellis/tasks/10-28-workflow-design-v48-0-1-audit/research'
MAIN='docs/workflows/workflow-design.md'; COMP='docs/workflows/依赖机制设计说明.md'
SPEC='.trellis/spec/docs/index.md'; GUIDE='.trellis/spec/guides/design-review-thinking-guide.md'
BASE=json.loads((REC/'followup-v50-baseline.json').read_text())
REPLACEMENTS=[]


def add(ident,path,anchor,old,new,acceptance,reason):
    REPLACEMENTS.append(dict(ID=ident,文件=path,锚点=anchor,old=old,new=new,验收位=acceptance,说明=reason))


add('V50-01',MAIN,'§4.4 族2标题',
    '| **活动期建边后随前置归档** |',
    '| **活动期建边 / 返工加边后随前置归档** |',
    'probe新标题=1、旧标题=0；v50族表枚举回查','P4标题与两个成员同宽')
add('V50-02',MAIN,'§7.7 类型5改判放弃-一般',
    '（只借用该步的删边动作，不重新发起放弃），最后归档旧任务；**项目层任务 P**',
    '（只借用该步的删边动作，不重新发起放弃），最后归档旧任务（已归档者不重复归档）；**项目层任务 P**',
    '类型5四分支归档守卫矩阵=4/4','P1')
add('V50-03',MAIN,'§7.7 类型5改判放弃-P',
    '改判放弃-P 行不新增写入），最后归档旧任务；旧 P 已归档或',
    '改判放弃-P 行不新增写入），最后归档旧任务（已归档者不重复归档）；旧 P 已归档或',
    '类型5四分支归档守卫矩阵=4/4','P1；明示本输入可已归档')
add('V50-04',MAIN,'§7.7 类型1一般任务',
    '补齐删边（旧任务已归档，不重复归档）',
    '补齐删边（已归档者不重复归档）',
    'probe统一归档守卫=5个规范位','P6；统一同类词面')
old_row3='| 存在返工任务记录、无未归档 R，但 T 的前置集合不全正常 | 按第三段的下沉规则先开工该未完成前置（同进行中目标的处置），完成后回本段按 §6.4 第 5 步清挂起；该前置为“异常”按 §7.4、为“正常但未归档”按类型 3；链上无就绪任务时报告阻塞 |'
new_row3='| 存在返工任务记录、无未归档 R，但 T 的前置集合不全正常 | 对该未完成前置逐项分流：“异常”按 §7.4、“正常但未归档”按类型 3；前置本身挂起时，以它为“对应 T”回到本段并完整匹配本表（有未归档 R 按第 1 行进入 R，满足 §6.4 第 5 步按第 2 行清除该前置的挂起，无返工任务记录按第 4 行处理）；其余普通未完成前置按第三段下沉规则先开工该未完成前置（同进行中目标的处置）；前置完成后回 T 所在本段按 §6.4 第 5 步评估清挂起；递归处理后仍无就绪任务时报告阻塞 |'
add('V50-06',MAIN,'§9.1 第二段挂起行第三行',old_row3,new_row3,
    'probe挂起下沉递归=1；D3递归状态表；自检','P2；对子任务状态递归匹配第二段，不增加机制')
old_row1='| 对应 T 有未归档返工任务 R | 进入 R；R 自身未就绪时按第三段处理 R 的前置 |'
new_row1='| 对应 T 有未归档返工任务 R | R 自身挂起时以 R 为“对应 T”回到本段并匹配各行；否则进入 R（R 自身未就绪时按第三段处理 R 的前置） |'
add('V50-07',MAIN,'§9.1 第二段挂起行第一行',old_row1,new_row1,
    'probe返工任务递归挂起=1；D3递归状态表','P2；同一挂起上下文规则覆盖返工子任务')
add('V50-08',MAIN,'§9.1 说明区下沉范围',
    '- **下沉是『当前任务』行内的分支，不是新的路由**（分支性质）：沿未完成前置链下行取链上最早就绪的图内任务（§7.6 排序）；链上无就绪任务时按 §7.7 等待行处置（异常前置按 §7.4、“正常但未归档”前置按类型 3）；仍无出口则报告阻塞；**终止于 DAG 无环（不变量 4）**。',
    '- **下沉是『当前任务』行与第二段第 3 行内的分支，不是新的路由**：沿未完成前置链下行取链上最早就绪的图内任务（§7.6 排序）；下沉目标前置本身挂起时，以它为第二段的“对应 T”递归匹配本段；异常前置按 §7.4、“正常但未归档”前置按类型 3；递归处理后仍无就绪任务则报告阻塞；**终止于 DAG 无环（不变量 4）**。',
    'probe新说明=1、旧说明=0；引用命中D2','P3')
old_84='按 §9.1 第二段的对应行先开工该未完成前置，完成后回本段清挂起；该前置为异常按 §7.4、为“正常但未归档”按类型 3'
new_84='按 §9.1 第二段的对应行递归处理该未完成前置（其本身挂起时以其为本段上下文）；该前置完成后回本段清挂起；该前置为异常按 §7.4、为“正常但未归档”按类型 3'
add('V50-09',MAIN,'§8.4 第二段挂起摘要',old_84,new_84,
    'probe8.4递归引用=1；引用命中D2','P2；摘要引用式随源更新')
old_self='一次挂起任务在返工期间被加入未完工前置（迭代期建边）→ 返工完成后不清挂起 → 按 §9.1 第二段开工该未完成前置 → 前置完成后清挂起 → 继续 T'
new_self='一次挂起任务 T 在返工期间被加入未完工前置 Q（迭代期建边）→ Q 自身挂起且有未归档 R_Q（Q 的其余前置均满足）→ R_T 完成后不清 T 挂起 → 按 §9.1 第二段以 Q 为上下文进入 R_Q → R_Q 完成后按 §6.4 第 5 步清 Q 挂起并继续 Q → Q 完成后按 §6.4 第 5 步评估清 T 挂起 → 继续 T'
add('V50-10',MAIN,'§10 挂起递归自检',old_self,new_self,
    'probeQ挂起用例=1；D3 recursive state case','P2')

add('V50-context',MAIN,'§9.1 第二段上下文定义',
    '本段只处理“该任务等待返工”这一件事，下一列的“对应 T”即当前任务或该挂起任务：',
    '本段只处理“该任务等待返工”这一件事，下一列的“对应 T”即当前任务、该挂起任务或行内递归指定的挂起任务；递归只切换本次判定上下文，不据此改写当前任务指针：',
    'D3递归状态表；probe上下文=1；指针边界不变','P2；显式接纳行内递归上下文')
add('V50-mirror-r',MAIN,'§8.4 第二段返工引用',
    '有未归档 R → 进入 R（R 自身未就绪时按本段以外的方式处理 R 的前置）',
    '有未归档 R → 按 §9.1 第二段第 1 行处理 R（含 R 自身挂起的递归入口）',
    'D2命中§9.1第二段行1；probe引用=1','P2；嵌套返工摘要降为引用')


def apply_one(text,item):
    old,new=item['old'],item['new']
    assert text.count(old)==1,(item['ID'],'old',text.count(old))
    if new: assert text.count(new)==0,(item['ID'],'new-exists',text.count(new))
    return text.replace(old,new,1)


def main():
    current=(ROOT/MAIN).read_text()
    for path,expected in BASE['sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected,(path,'post-scan drift')
    for item in REPLACEMENTS:
        current=apply_one(current,item)
    (ROOT/MAIN).write_text(current)
    manifest=REC/'fix-manifest-v50.tsv'
    with manifest.open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=['ID','文件','锚点','old','new','验收位','说明'],delimiter='\t')
        writer.writeheader(); writer.writerows(REPLACEMENTS)
    print('applied source replacements',len(REPLACEMENTS),'manifest',manifest)


if __name__=='__main__': main()
