#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D1 状态枚举门（v50 收口批次 + 复核轮扩展）.

把 workflow-design.md 的三段入口路由（第一段全局旁路 4 条、第二段挂起 4 行、
第三段按项目层阶段 7/5 行）编码为单任务判定网格，对全部轴值组合断言：
每个可达格恰好落到一行（转发行除外，见 redirect 标记）、出口非空且「报告阻塞」
只作兜底、委派目标可在文档中解析到具体类型号/表行/步骤、无互斥动作并存。

复核轮扩展（对 externally-review 发现的三项修正）：
- 网格补两根承重轴（succ 替换指向/继任者形态 × down 未归档下游指向），
  disposition_unfinished 改为 §7.4 的字段谓词（不再用 phase 代理）；
  M1_v41_predicate 改回真旧谓词（「替换指向为空」作终态必要条件），
  使「替换正常完成后重启被判未完成」的 v41 假阳性可在门内复现；
- 链级场景补 S7（放弃-新建替代的收尾继任面）；变异补 M6（删「留有继任者」
  半句 → S7 必红）；
- 新增「处置形态全集」断言（替换 / 放弃-删边 / 放弃-新建替代 / 类型 1 补建 /
  类型 5 补建，每个形态都必须解析出收尾对象或重定义出口）——修与验不再共享
  同一份位点枚举，形态清单驱动；
- run_mutation 接受注入文本（text=…），测试不得覆写真实文档。

纯标准库；无网络、无子进程调模型；只读两份设计文档；除 stdout 不写文件。

编码约定：每个 Row 的 src 字段即该行判定/出口的文档来源标注（§4.8），
check_delegations 自检每个编码行都带 src。
"""
import argparse
import itertools
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MAIN_DOC = REPO / 'docs/workflows/workflow-design.md'
COMP_DOC = REPO / 'docs/workflows/依赖机制设计说明.md'

# ---------------------------------------------------------------------------
# 文档解析（只依赖稳定表头文案，不依赖行号；失败报「定位失败」不静默 0 行）
# ---------------------------------------------------------------------------

SEP_RE = re.compile(r'^\|[\s\-:|]+\|$')


class Doc:
    def __init__(self, text):
        self.lines = text.split('\n')

    @classmethod
    def load(cls, path):
        return cls(path.read_text(encoding='utf-8'))

    def table_rows(self, header_sub, occurrence=1):
        """返回第 occurrence 张以 header_sub 命中表头的表的数据行（去表头与分隔行）。"""
        n = 0
        for i, l in enumerate(self.lines):
            s = l.strip()
            if s.startswith('|') and header_sub in s:
                n += 1
                if n == occurrence:
                    rows = []
                    j = i + 2  # 跳过表头与 |---| 行
                    while j < len(self.lines):
                        t = self.lines[j].strip()
                        if t.startswith('|') and not SEP_RE.match(t):
                            rows.append(t)
                            j += 1
                        else:
                            break
                    if not rows:
                        raise SystemExit(f'定位失败: 表 «{header_sub}» 第 {occurrence} 处无数据行')
                    return rows
        raise SystemExit(f'定位失败: 未找到表 «{header_sub}»（第 {occurrence} 处）')

    def section(self, title):
        """返回 '### N. title'（或 '## …'）章节标题行到下一个同级/更高级标题前的行。"""
        pat = re.compile(r'^#{2,4}\s+' + re.escape(title) + r'\s*$')
        out, in_sec = [], False
        for l in self.lines:
            if re.match(r'^#{1,4}\s', l):
                if in_sec:
                    break
                if pat.match(l):
                    in_sec = True
            if in_sec:
                out.append(l)
        if not out:
            raise SystemExit(f'定位失败: 未找到章节 «{title}»')
        return out


def parse_main(text=None):
    d = Doc(text if text is not None else MAIN_DOC.read_text(encoding='utf-8'))
    seg1 = [l for l in d.lines if re.match(
        r'^- \*\*(模块不可用|完整性与恢复分流|旧口径存量挂起尚未移交|需要改基线)\*\*', l)]
    tables = {
        '第一段': len(seg1),
        '第二段': len(d.table_rows('| 当前情况 | 下一步 |', 1)),
        '未收尾': len(d.table_rows('| 当前情况 | 下一步 |', 2)),
        '已收尾': len(d.table_rows('| 当前情况 | 下一步 |', 3)),
        '表4-2': len(d.table_rows('| # | 从 | 到 | 触发 | 写入者 / 说明 |')),
        '组合表': len(d.table_rows('| 组合 | 判定 | 出口 |', 1)),
        '族表': len(d.table_rows('| 族 | 内容 | 受 §7.5 建边限制 |')),
        '§7.4': len(d.table_rows('| 账本状态 | 对下游 |')),
        '§6.4窗口': len(d.table_rows('| 窗口 | 已提交识别项 / 残留 | 恢复 |')),
        '§7.8矩阵': len(d.table_rows('| 写入路径 | 写入时点 | 指向终值 | 说明 / 原因终值 | 依据 |')),
    }
    return d, tables


# ---------------------------------------------------------------------------
# 委派目标解析（口径 12 的机械版）：出口引用必须解析到文档中的具体类型/表行/步骤
# ---------------------------------------------------------------------------

def build_delegations(d, comp=None):
    """返回 {委派名: (bool 可解析, 证据串)}，全部基于当前文档解析。"""
    if comp is None:
        comp = Doc.load(COMP_DOC)
    s77 = d.section('7.7 一致性与恢复')
    s76 = d.section('7.6 选择')
    s64 = d.section('6.4 返工')
    s67 = d.section('6.7 收尾任务')
    s65 = d.section('6.5 替换')
    seg2_rows = d.table_rows('| 当前情况 | 下一步 |', 1)
    t42 = d.table_rows('| # | 从 | 到 | 触发 | 写入者 / 说明 |')
    combo = d.table_rows('| 组合 | 判定 | 出口 |', 1)
    s74_rows = d.table_rows('| 账本状态 | 对下游 |')
    fam_rows = d.table_rows('| 族 | 内容 | 受 §7.5 建边限制 |')
    comp_s8 = comp.section('8. 一致性与恢复')

    def row_of(rows, key):
        for r in rows:
            if key in r:
                return r
        return None

    seg1_lines = [l for l in d.lines if '完整性与恢复分流' in l]
    fam2 = row_of(fam_rows, '活动期建边') or ''
    type5_line = None
    for l in s77:
        if '- **补建**' in l:
            type5_line = l
            break
    checks = {
        '类型1': ('已归档但账本不是合法终态', s77),
        '类型1_P分支': ('项目层任务 P 且尚无继任者', s77),
        '类型1_同款守卫': ('已归档者不重复归档', s77),
        '类型2': ('返工登记未完成，或未归档任务挂起但找不到返工任务', s77),
        '类型3': ('正常但未归档', s77),
        '类型4': ('无法解析或非法的记录 / 边', s77),
        '类型5': ('替换/放弃未完成', s77),
        '类型5唯一源': ('向前完成」的唯一源', s77),
        '类型5_补建守卫': ('已归档者不重复归档', type5_line or ''),
        '表4-2行3': ('按 §6.4 第 5 步判据', t42[2] if len(t42) >= 3 else ''),
        '§6.4第5步': ('挂起清除（唯一判据）', s64),
        '§7.6排序': ('任务创建时间', s76),
        '§7.4异常行': ('类型 5', row_of(s74_rows, '异常') or ''),
        '§7.4终态枝': ('无需处分动作', row_of(s74_rows, '异常') or ''),
        '§7.4继任者枝': ('继任者已建', row_of(s74_rows, '异常') or ''),
        '第二段行1': ('对应 T 有未归档返工任务 R', row_of(seg2_rows, '对应 T 有未归档返工任务 R') or ''),
        '第二段行3': ('递归处理后仍无就绪任务时报告阻塞', row_of(seg2_rows, '存在返工任务记录') or ''),
        '第二段行4': ('找不到返工任务记录', row_of(seg2_rows, '找不到返工任务记录') or ''),
        '组合表待重定义行': ('待重定义', row_of(combo, '待重定义') or ''),
        '组合表待重定义出口': ('人重定义收尾', row_of(combo, '待重定义') or ''),
        '§6.7收尾对象定义': ('收尾对象', s67),
        '§6.7收尾完成定义': ('收尾完成', s67),
        '§6.7替换继任句': ('继任者即收尾对象', s67),  # 继任规则存在即覆盖替换形态；S1 依赖
        '§6.7新建替代继任句': ('留有继任者（新建替代）时，继任者即收尾对象', s67),  # 复核轮 R1 后存在；S7 依赖
        '§6.7无继任者重定义句': ('无继任者（删边变体）时由人重新定义收尾任务', s67),  # E1/R1 后存在；S2 依赖
        '§9.1第一段类型1补齐': ('已归档但账本无记录 / 挂起（新发生的类型 1）同样在本段阻断', seg1_lines),
        '§6.5P解析': ('P 角色解析（唯一源）', s65),
        '族2成员': ('**建边 / 返工加边**（两端都在活动区时建立的边）', fam2),
        '族2标题': ('建边 / 返工加边', fam2),
        '产出态_补建': ('补建 → 新任务（无记录）+ 下游换依赖 + 旧任务已归档异常', comp_s8),
        '产出态_改判一般': ('改判放弃 → 已归档 + 异常 + 无指向（一般任务）', comp_s8),
        '产出态_改判P': ('或新 P 建立并重连（P 分支）', comp_s8),
        '产出态_无指向': ('无替换指向 → 下游删边 + 旧任务归档', comp_s8),
    }
    out = {}
    for name, (needle, scope) in checks.items():
        lines = scope if isinstance(scope, list) else [scope]
        ok = any(needle in l for l in lines)
        out[name] = (ok, f'«{needle}» 命中' if ok else f'«{needle}» 未解析到')
    return out


# ---------------------------------------------------------------------------
# 单任务网格模型。轴与取值全部来自文档（src 注释标注来源）。
# ---------------------------------------------------------------------------

STATUS = ['规划中', '进行中', '已归档']           # src: §4.2 任务状态（:244）
LEDGER = ['无记录', '挂起', '正常', '异常']        # src: §4.2 依赖状态（:246）
POINTER = ['无', '有效非挂起', '有效挂起', '无效']  # src: §3「当前任务」无效清单（:195）
PREREQ = ['全正常', '含未完工', '含挂起', '含异常', '含正常但未归档']  # src: §4.3 / §7.5
REWORK = ['无记录', '有未归档R', '有但全归档']      # src: §7.3 返工任务集合（:585）
REGIST = ['无', '合法未完成', '标记损坏']           # src: §6.4 / §7.7 类型 2/4（:640）
PHASE = ['项目层未收尾', '项目层已收尾']            # src: §6.5 / §9.1 第三段（:805）
SUCC = ['无指向', '指向未建', '指向已建']           # src: §7.4 表行承重字段（替换指向×继任者）
DOWN = ['无下游指向', '下游仍指向']                 # src: §7.4 表行承重字段（未归档下游指向）

AXES = [('status', STATUS), ('ledger', LEDGER), ('pointer', POINTER), ('prereq', PREREQ),
        ('rework', REWORK), ('registration', REGIST), ('phase', PHASE),
        ('succ', SUCC), ('down', DOWN)]

# 处置形态全集（复核轮新增的唯一断言清单；src: §6.5/§6.6/§7.7 类型 1/类型 5）。
# 每个形态都必须解析出一个收尾对象或重定义出口——修与验不再共享位点枚举。
DISPOSITION_FORMS = ['替换', '放弃-删边', '放弃-新建替代', '类型 1 补建', '类型 5 补建']

# 文档实测行数常量（元断言；与 parse_main 的实测三方比对）。
# 注意：任务书基线表写「已收尾表 = 6」，文档 §9.1 已收尾表实测为 5 行；本门按文档
# 实际编码为 5，差异登记于本轮报告与 known-residuals.md，不新增表行凑数。
EXPECTED_TABLES = {'第一段': 4, '第二段': 4, '未收尾': 7, '已收尾': 5, '表4-2': 7,
                   '组合表': 12, '族表': 4, '§7.4': 4, '§6.4窗口': 9, '§7.8矩阵': 14}


def eff_pointer(c):
    """§3 推导：指针是提示，有效性按 §3 无效清单逐条导出（src: §3 :195）。"""
    if c['pointer'] == '无':
        return '无'
    st, lg, pq = c['status'], c['ledger'], c['prereq']
    if st == '已归档':
        return '无效'                                    # src: §3「指向已归档」
    if lg in ('正常', '异常'):
        return '无效'                                    # src: §3「正常但未归档」/「未归档且账本异常」
    if st == '规划中' and pq != '全正常':
        return '无效'                                    # src: §3「规划中且前置未满足」
    return '有效挂起' if lg == '挂起' else '有效非挂起'


def disposition_unfinished(c):
    """§7.4 表行字段谓词（src: §7.4 :601，唯一源；不再用 phase 代理）。

    未完成 = 有合法替换指向而继任者未建、未归档下游仍指向它、该任务未归档——三者任一。
    """
    if c['status'] != '已归档':
        return True                                 # src: 该任务未归档
    if c['down'] == '下游仍指向':
        return True                                 # src: 未归档下游仍指向该任务
    if c['succ'] == '指向未建':
        return True                                 # src: 有合法替换指向而继任者未建
    return False


def successor_terminal(c):
    """已归档 + 异常 + 处分终态 + 指向合法继任者（src: §7.4 终态枝 / §6.5 :510）。"""
    return (c['status'] == '已归档' and c['ledger'] == '异常'
            and c['succ'] == '指向已建' and c['down'] == '无下游指向')


def resolved_phase(c):
    """src: §9.1 :805 / §6.5——项目层是否收尾统一按 §6.5 解析；已归档+正常+前置全正常
    即正常完成的 P 终点，阶段轴取值被 §6.5 解析覆写（§6.5 P 解析表 :506）。"""
    if c['status'] == '已归档' and c['ledger'] == '正常' and c['prereq'] == '全正常':
        return '项目层已收尾'
    return c['phase']


def ready_exists(c):
    """单任务保守世界：本任务自身就绪（§3 就绪 :197），或有未归档返工任务 R。
    src: §9.1 未收尾表「存在就绪的图内任务」行（:816）。"""
    self_ready = (c['status'] in ('规划中', '进行中') and c['ledger'] == '无记录'
                  and c['prereq'] == '全正常')
    return self_ready or c['rework'] == '有未归档R'


def seg3_input_recovered(c):
    """src: §9.1 :805「待类型 1/4/5 的 P 输入先恢复，不因归档而提前进入已收尾表」。
    第三段表只接收已恢复输入：已归档任务允许的只剩 正常（终态）与 异常且处分已到终态。"""
    if c['status'] != '已归档':
        return True
    if c['ledger'] in ('无记录', '挂起'):
        return False                                     # 类型 1，第一段 F2d 阻断
    if c['ledger'] == '正常' and c['prereq'] != '全正常':
        return False                                     # 组合表行 2，第一段 F2e 阻断
    if c['ledger'] == '异常' and disposition_unfinished(c):
        return False                                     # 类型 5，第一段 F2c 阻断
    return True


class Row:
    __slots__ = ('seg', 'rid', 'name', 'pred', 'actions', 'delegations', 'src', 'flags')

    def __init__(self, seg, rid, name, pred, actions, delegations, src, flags=()):
        self.seg, self.rid, self.name = seg, rid, name
        self.pred, self.actions = pred, list(actions)
        self.delegations = list(delegations)
        self.src, self.flags = src, tuple(flags)


def build_rows(mutations=()):
    """编码行全集。mutations 是已应用的变异名集合（M1 改 §7.4 谓词编码）。"""
    M1 = 'M1_v41_predicate' in mutations

    def disp_unfin(c):
        if M1:
            # M1_v41（真旧谓词，src: 附录 C v41 记录 :1042）：终态要求「替换指向为空」，
            # 即 终态 = 已归档 ∧ 无替换指向 ∧ 下游已不指向。替换/新建替代/类型 1-P/
            # 类型 5 补建保留指向 → 正常完成后重启被判未完成（v41 假阳性）。
            return not (c['status'] == '已归档' and c['succ'] == '无指向'
                        and c['down'] == '无下游指向')
        return disposition_unfinished(c)

    rows = []
    # ---- 第一段 全局旁路（4 条；src: §9.1 :791–794）----
    rows.append(Row(1, 'F1', '模块不可用',
                    lambda c: False,  # 外部输入，非轴可导（src: §9.1 :791）
                    ['按 §9.4 卸载；修复后重装；不绕过机制'], [], 'src: §9.1 :791 模块不可用'))
    rows.append(Row(1, 'F2a', '完整性分流·标记损坏先类型 4',
                    lambda c: c['registration'] == '标记损坏',
                    ['按 §7.7 类型 4 修复字段'], ['类型4'],
                    'src: §9.1 :792 + §7.7 分类前置守卫 :650'))
    rows.append(Row(1, 'F2b', '完整性分流·合法未完成登记先类型 2',
                    lambda c: c['registration'] == '合法未完成',
                    ['按 §6.4 登记序列恢复 / 取消（§7.7 类型 2 入口）'], ['类型2'],
                    'src: §9.1 :792 + §7.7 分类前置守卫 :650'))
    rows.append(Row(1, 'F2c', '完整性分流·未完成处分走类型 5',
                    lambda c: (c['registration'] == '无' and c['ledger'] == '异常'
                               and disp_unfin(c)),
                    ['按 §7.7 类型 5 向前完成（先补建/重连、后归档）'], ['类型5', '类型5唯一源'],
                    'src: §9.1 :792 + §7.4 表行未完成枝 :601'))
    rows.append(Row(1, 'F2d', '完整性分流·新发生类型 1 阻断（E4）',
                    lambda c: (c['registration'] == '无' and c['status'] == '已归档'
                               and c['ledger'] in ('无记录', '挂起')),
                    ['本段阻断，待人确认后按 §7.7 类型 1 修复'], ['类型1', '§9.1第一段类型1补齐'],
                    'src: §9.1 :792（E4 后含「已归档但账本无记录 / 挂起…按类型 1 修复」）'))
    rows.append(Row(1, 'F2e', '完整性分流·已归档正常前置非正常走类型 4',
                    lambda c: (c['registration'] == '无' and c['status'] == '已归档'
                               and c['ledger'] == '正常' and c['prereq'] != '全正常'),
                    ['按 §7.7 组合表行 2 → 类型 4 修复边'], ['类型4'],
                    'src: §7.7 组合表行 2 :656 / §6.5 P 解析表 :507'))
    rows.append(Row(1, 'F3', '旧口径存量挂起尚未移交',
                    lambda c: False,  # 项目级持久事实，非轴可导（src: §6.4 移交条款 :459）
                    ['按 §6.4 人确认后才能评估与选择'], [], 'src: §9.1 :793'))
    rows.append(Row(1, 'F4', '需要改基线',
                    lambda c: False,  # 人决定，非轴可导（src: §9.1 :794）
                    ['回到 §5.5'], [], 'src: §9.1 :794'))

    # ---- 第二段 挂起（4 行；src: §9.1 :798–803）----
    def seg2_entry(c):
        return (c['ledger'] == '挂起' and c['status'] != '已归档'
                and c['registration'] == '无')
    rows.append(Row(2, 'H1', '对应 T 有未归档返工任务 R',
                    lambda c: seg2_entry(c) and c['rework'] == '有未归档R',
                    ['进入 R（R 自身挂起时以 R 为「对应 T」回本段；R 未就绪时前置逐项分流）'],
                    ['第二段行1', '类型5'],
                    'src: §9.1 :800'))
    rows.append(Row(2, 'H2', '满足 §6.4 第 5 步清除条件',
                    lambda c: (seg2_entry(c) and c['rework'] == '有但全归档'
                               and c['prereq'] == '全正常'),
                    ['清除挂起（表 4-2 行 3）；T 回到就绪集'], ['表4-2行3', '§6.4第5步'],
                    'src: §9.1 :801', flags=('clear_suspend',)))
    rows.append(Row(2, 'H3', '有返工记录、无未归档 R，前置不全正常',
                    lambda c: (seg2_entry(c) and c['rework'] == '有但全归档'
                               and c['prereq'] != '全正常'),
                    ['递归处理未完成前置（异常按 §7.4、正常但未归档按类型 3、挂起以它为'
                     '「对应 T」回本段）；全部处理完回本段按 §6.4 第 5 步复评清挂起；'
                     '递归后仍无就绪任务时报告阻塞'],
                    ['第二段行3', '§6.4第5步'],
                    'src: §9.1 :802', flags=('may_block',)))
    rows.append(Row(2, 'H4', '找不到返工任务记录',
                    lambda c: seg2_entry(c) and c['rework'] == '无记录',
                    ['按 §7.7 类型 2 对账修复'], ['类型2', '第二段行4'], 'src: §9.1 :803'))

    # ---- 第三段 非挂起（未收尾 7 行 / 已收尾 5 行；src: §9.1 :809–827）----
    def s3(c):
        return seg3_input_recovered(c)

    def p_ok(c):
        return resolved_phase(c) == '项目层未收尾'

    def no_cur(c):
        return eff_pointer(c) in ('无', '无效')

    rows.append(Row(3, 'U1', '未收尾·有当前任务、按 §3 有效且非挂起',
                    lambda c: s3(c) and p_ok(c) and eff_pointer(c) == '有效非挂起',
                    ['继续当前任务（P 自身/返工任务/图内/图外）；前置不全正常时沿未完成前置链'
                     '下沉，先开工链上最早就绪的图内任务，完成后回本任务收尾'],
                    ['§7.6排序'], 'src: §9.1 :811'))
    rows.append(Row(3, 'U2', '未收尾·有当前任务，但按 §3 无效',
                    lambda c: s3(c) and p_ok(c) and eff_pointer(c) == '无效',
                    ['视为无当前任务，看下面各行（转发行，不独占）'],
                    [], 'src: §9.1 :812', flags=('redirect',)))
    rows.append(Row(3, 'U3', '未收尾·无当前任务、无项目层任务',
                    lambda c: False,  # 单任务网格中任务即 P，P 恒存在；场景 S3 断言不落本行
                    ['启动 P：立项 + 基线 + 任务图'], [], 'src: §9.1 :813'))
    rows.append(Row(3, 'U4', '未收尾·P 正常但未归档',
                    lambda c: (s3(c) and p_ok(c) and no_cur(c)
                               and c['status'] != '已归档' and c['ledger'] == '正常'),
                    ['按 §7.7 类型 3 修复后再继续'], ['类型3'], 'src: §9.1 :814'))
    rows.append(Row(3, 'U5', '未收尾·P 前置全正常、账本无记录',
                    lambda c: (s3(c) and p_ok(c) and no_cur(c)
                               and c['status'] != '已归档' and c['ledger'] == '无记录'
                               and c['prereq'] == '全正常'),
                    ['只执行 P'], [], 'src: §9.1 :815'))
    rows.append(Row(3, 'U6', '未收尾·前置含非正常且存在就绪图内任务',
                    lambda c: (s3(c) and p_ok(c) and no_cur(c)
                               and c['status'] != '已归档' and c['ledger'] == '无记录'
                               and c['prereq'] != '全正常' and ready_exists(c)),
                    ['取最早就绪的图内任务（按 §7.6）'], ['§7.6排序'], 'src: §9.1 :816'))
    rows.append(Row(3, 'U7', '未收尾·前置含非正常且无就绪图内任务',
                    lambda c: (s3(c) and p_ok(c) and no_cur(c)
                               and c['status'] != '已归档' and c['ledger'] == '无记录'
                               and c['prereq'] != '全正常' and not ready_exists(c)),
                    ['等前置；前置为「正常但未归档」先按类型 3 修复该前置；异常前置按 §7.4 处置'],
                    ['类型3', '§7.4异常行'], 'src: §9.1 :817'))

    rows.append(Row(3, 'C1', '已收尾·有当前任务、按 §3 有效且非挂起',
                    lambda c: s3(c) and not p_ok(c) and eff_pointer(c) == '有效非挂起',
                    ['继续当前任务；前置不全正常时沿未完成前置链下沉，完成后回本任务收尾'],
                    ['§7.6排序'], 'src: §9.1 :823'))
    rows.append(Row(3, 'C2', '已收尾·有当前任务，但按 §3 无效',
                    lambda c: s3(c) and not p_ok(c) and eff_pointer(c) == '无效',
                    ['视为无当前任务，看下面各行（转发行，不独占）'],
                    [], 'src: §9.1 :824', flags=('redirect',)))
    rows.append(Row(3, 'C3', '已收尾·存在就绪的图内任务',
                    lambda c: (s3(c) and not p_ok(c) and no_cur(c) and ready_exists(c)
                               and not successor_terminal(c)),
                    ['取 DAG 视图中最早就绪的图内任务（按创建时间）'], ['§7.6排序'], 'src: §9.1 :825'))
    # 收尾完成是链级判定（收尾对象 = 链尾收尾任务）；单任务网格里把「本任务即
    # 已归档+正常+前置全正常」的终态编为本行，链级真值由 S1/S2 场景断言。
    rows.append(Row(3, 'C4', '已收尾·无就绪、收尾完成（按 §6.7）',
                    lambda c: (s3(c) and not p_ok(c) and no_cur(c) and not ready_exists(c)
                               and c['status'] == '已归档' and c['ledger'] == '正常'
                               and c['prereq'] == '全正常'),
                    ['迭代期普通任务'], ['§6.7收尾完成定义'], 'src: §9.1 :826 + §6.7 :545'))
    rows.append(Row(3, 'C5', '已收尾·无就绪、收尾未完成',
                    lambda c: (s3(c) and not p_ok(c) and no_cur(c) and not ready_exists(c)
                               and not successor_terminal(c)
                               and not (c['status'] == '已归档' and c['ledger'] == '正常'
                                        and c['prereq'] == '全正常')),
                    ['按 §7.7 完整性自检 / 对账；异常前置按 §7.4 处置；无收尾对象时按组合表'
                     '「待重定义」行（人重定义收尾）'],
                    ['组合表待重定义行', '组合表待重定义出口', '§7.4异常行'],
                    'src: §9.1 :827', flags=('may_block',)))
    # R0a/R0b（复核轮新增编码）：已归档 + 异常 + 处分已到终态的「已解决终态记录」——
    # §7.4 判无需处分动作，路由对象沿替换指向移交继任者或回归就绪选择（§6.5 :510）。
    rows.append(Row(3, 'R0a', '已解决终态记录·指向合法继任者',
                    lambda c: (s3(c) and successor_terminal(c)),
                    ['无需处分动作（§7.4 终态枝）；沿替换指向继续解析，对象移交继任者'
                     '（§6.5），本任务不再作为路由对象'],
                    ['§7.4终态枝', '§6.5P解析'], 'src: §7.4 :601 终态枝 + §6.5 :510'))
    rows.append(Row(3, 'R0b', '已解决终态记录·删边变体完成（无指向）',
                    lambda c: (s3(c) and p_ok(c) and c['status'] == '已归档'
                               and c['ledger'] == '异常' and not disposition_unfinished(c)
                               and c['succ'] == '无指向'),
                    ['无需修复（放弃-删边变体终态）；继续按第三段就绪选择（§7.6），'
                     '项目层对象按 §6.5 解析'],
                    ['§7.6排序', '§6.5P解析'], 'src: §7.4 :601 终态枝 + §9.1 :805'))
    return rows


# ---------------------------------------------------------------------------
# 网格求值与断言
# ---------------------------------------------------------------------------

def resolve_cell(rows, c):
    """三段逐段判定。段内转发行（redirect）不独占：与其并存的落点行唯一即算命中。
    返回 (命中行列表, 落点行或 None)。"""
    for seg in (1, 2, 3):
        hits = [r for r in rows if r.seg == seg and r.pred(c)]
        if not hits:
            continue
        landing = [r for r in hits if 'redirect' not in r.flags]
        redirects = [r for r in hits if 'redirect' in r.flags]
        if len(landing) == 1 and len(hits) == len(landing) + len(redirects) and len(redirects) <= 1:
            return hits, landing[0]
        return hits, None  # 0 落点 或 多落点 → 红
    return [], None


def run_grid(rows):
    """跑全部轴值组合（不抽样、不筛「不可达」）。返回 (红格清单, 统计)。"""
    reds = []
    dup = unresolved = 0
    combos = 0
    for values in itertools.product(*[vals for _, vals in AXES]):
        c = dict(zip([n for n, _ in AXES], values))
        combos += 1
        hits, winner = resolve_cell(rows, c)
        problems = []
        if len(hits) == 0:
            problems.append('0 命中：三段均无落点（待恢复输入不得进第三段，第一段应已阻断）')
            unresolved += 1
        elif winner is None:
            problems.append(f'多落点（{len([r for r in hits if "redirect" not in r.flags])} 行）: '
                            + '+'.join(r.rid for r in hits))
            dup += 1
        else:
            acts = winner.actions
            if not acts or all(not a.strip() for a in acts):
                problems.append(f'{winner.rid} 出口为空')
            flat = '；'.join(acts)
            if '报告阻塞' in flat:
                # 「报告阻塞」只能作兜底：必须同时存在向前动作
                if not any(k in flat for k in ('递归', '自检', '对账', '重定义', '等前置', '取', '开工')):
                    problems.append(f'{winner.rid} 「报告阻塞」无向前动作兜底')
            if 'clear_suspend' in winner.flags and 'may_block' in winner.flags:
                problems.append(f'{winner.rid} 同时清除挂起与报告阻塞（互斥动作并存）')
        if problems:
            reds.append((c, problems))
    return reds, {'combos': combos, 'red': len(reds), 'dup': dup, 'unresolved': unresolved}


def check_delegations(rows, delegations, tables):
    """断言：每个编码行都带 src 注释；委派目标全部可解析；行数与文档一致。"""
    errs = []
    for r in rows:
        if not (r.src or '').strip():
            errs.append(f'编码残缺: {r.rid} 缺 src 注释')
        if not r.actions:
            errs.append(f'编码残缺: {r.rid} 缺出口')
        for dep in r.delegations:
            ok, ev = delegations.get(dep, (False, '未登记的委派名'))
            if not ok:
                errs.append(f'{r.rid} 委派 {dep} 解析失败（{ev}）')
    for name, exp in EXPECTED_TABLES.items():
        if tables[name] != exp:
            errs.append(f'表行数不等: {name} 文档实测 {tables[name]} ≠ 已编码 {exp}')
    return errs


# ---------------------------------------------------------------------------
# 链级结构场景（单格网格表达不了的；每条断言每步动作存在 + 终态唯一）。
# 场景清单以 run_scenarios 内的 expect(...) 调用为唯一源；注释不写数目。
# ---------------------------------------------------------------------------

def make_cell(**kw):
    c = {'status': '规划中', 'ledger': '无记录', 'pointer': '无', 'prereq': '全正常',
         'rework': '无记录', 'registration': '无', 'phase': '项目层未收尾',
         'succ': '无指向', 'down': '无下游指向'}
    c.update(kw)
    return c


def type5_guard_sites(d):
    """类型 5 四个终归档位点的守卫核对（src: §7.7 :682–684；v50 探针口径 4 位点）。"""
    s77 = d.section('7.7 一致性与恢复')
    sites = {}
    for l in s77:
        if '- **补建**' in l:
            sites['补建'] = l.count('已归档者不重复归档')
        if '- **改判为放弃**' in l:
            sites['改判放弃-一般'] = 0
            sites['改判放弃-P'] = 0
            m = re.search(r'\*\*一般任务\*\*(.*?)\*\*项目层任务 P\*\*(.*)', l)
            if m:
                sites['改判放弃-一般'] = m.group(1).count('已归档者不重复归档')
                sites['改判放弃-P'] = m.group(2).count('已归档者不重复归档')
        if '- **无替换指向**' in l:
            sites['无指向'] = l.count('已归档者不重复归档')
    return sites


def run_scenarios(rows, d, dele):
    out = []

    def expect(name, cond, detail=''):
        out.append({'scenario': name, 'ok': bool(cond), 'detail': detail})

    # S1（F1，改 E1 前红、后绿）：替换链尾 S → 继任者 S′ 正常归档 → 收尾对象=S′，收尾完成。
    s67_ok = dele['§6.7替换继任句'][0]
    c = make_cell(status='已归档', ledger='正常', prereq='全正常', phase='项目层已收尾')
    hits, winner = resolve_cell(rows, c)
    landed = winner is not None and len(hits) >= 1
    non_block = landed and '报告阻塞' not in '；'.join(winner.actions)
    if s67_ok:
        ok = landed and non_block and winner.rid == 'C4'
        expect('S1', ok, f'§6.7 含「被替换时继任者即收尾对象」；收尾对象解析到 S′（已归档+正常），'
                        f'收尾完成 = true；落点 {winner.rid if winner else "无"}，'
                        f'出口「{'；'.join(winner.actions) if winner else ""}」非报告阻塞')
    else:
        expect('S1', False, '§6.7 收尾对象定义缺「被替换时继任者即收尾对象」——'
                            '替换后收尾对象为空，唯一出口退化为报告阻塞/待人重定义（红）')

    # S2：放弃链尾（删边变体）→ 无收尾对象 + 尾端异常且处分已到终态 → 待重定义行。
    c = make_cell(status='已归档', ledger='异常', prereq='全正常', phase='项目层已收尾',
                  rework='无记录', succ='无指向', down='无下游指向')
    hits, winner = resolve_cell(rows, c)
    ok = winner is not None and any('重定义' in a for a in winner.actions)
    expect('S2', ok, f'放弃删边变体完成 → 尾端已归档+异常+终态 → 落点 '
                     f'{winner.rid if winner else "无"}，出口含人重定义收尾')

    # S3：替换 P → P 解析沿替换指向到继任者 → 不落「启动 P」重建立项。
    c = make_cell(status='进行中', ledger='无记录', prereq='全正常', phase='项目层未收尾')
    hits, winner = resolve_cell(rows, c)
    u3_hit = any(r.rid == 'U3' for r in hits)
    expect('S3', winner is not None and winner.rid == 'U5' and not u3_hit,
           f'P 解析到继任者（§6.5）→ 落点 {winner.rid if winner else "无"}（只执行 P），'
           f'未重建立项（U3 未命中）')

    # S4：已归档 + 无记录 P → 类型 1 → P 分支补建 → 解析到新 P。
    c = make_cell(status='已归档', ledger='无记录', prereq='全正常', phase='项目层未收尾')
    hits, winner = resolve_cell(rows, c)
    t1_hit = winner is not None and '类型 1' in '；'.join(winner.actions)
    expect('S4', t1_hit and dele['类型1_P分支'][0],
           f'已归档+无记录 P → 第一段阻断按类型 1（落点 {winner.rid if winner else "无"}）；'
           f'§7.7 P 分支补建新 P 可解析={dele["类型1_P分支"][0]}')

    # S5（§10 场景）：挂起 T + 前置 Q 挂起且有未归档 R_Q → 以 Q 递归 → 进 R_Q → 清 Q → 清 T。
    steps = []
    cT = make_cell(ledger='挂起', status='进行中', prereq='含挂起', rework='有但全归档')
    _, w = resolve_cell(rows, cT)
    steps.append(('T:挂起+Q未满足→H3', w.rid if w and w.rid == 'H3' else None))
    cQ = make_cell(ledger='挂起', status='进行中', prereq='全正常', rework='有未归档R')
    _, w = resolve_cell(rows, cQ)
    steps.append(('Q:挂起+未归档R_Q→H1', w.rid if w and w.rid == 'H1' else None))
    cQ2 = make_cell(ledger='挂起', status='进行中', prereq='全正常', rework='有但全归档')
    _, w = resolve_cell(rows, cQ2)
    steps.append(('Q:R_Q全归档+前置全正常→H2', w.rid if w and w.rid == 'H2' else None))
    cT2 = make_cell(ledger='挂起', status='进行中', prereq='全正常', rework='有但全归档')
    _, w = resolve_cell(rows, cT2)
    steps.append(('T:回本段复评→H2', w.rid if w and w.rid == 'H2' else None))
    expect('S5', all(s[1] for s in steps), '; '.join(f'{k}={v}' for k, v in steps))

    # S6：类型 5 四分支各含「已归档者不重复归档」守卫，终态唯一。
    sites = type5_guard_sites(d)
    guards_ok = (len(sites) == 4 and all(v >= 1 for v in sites.values()))
    term_ok = all(dele[k][0] for k in
                  ('产出态_补建', '产出态_改判一般', '产出态_改判P', '产出态_无指向'))
    expect('S6', guards_ok and term_ok,
           f'守卫位点 {sites}（4/4）；四分支产出态在配套 §8 类型 5 各自唯一可解析={term_ok}')

    # S7（复核轮新增）：放弃-新建替代的收尾继任面——收尾任务 S 放弃且留有继任者 S″，
    # S″ 继承前置、完成后正常归档 → S″ 即收尾对象，收尾完成，不落「待重定义」死路。
    s67_alt_ok = dele['§6.7新建替代继任句'][0]
    if s67_alt_ok:
        c = make_cell(status='已归档', ledger='正常', prereq='全正常',
                      phase='项目层已收尾', succ='指向已建', down='无下游指向')
        # S″ 自身：正常归档 → 收尾对象=S″ → C4（迭代期普通任务），非报告阻塞
        hits, winner = resolve_cell(rows, c)
        ok = (winner is not None and winner.rid == 'C4'
              and '报告阻塞' not in '；'.join(winner.actions))
        expect('S7', ok, f'§6.7 含「留有继任者（新建替代）时继任者即收尾对象」；替代任务 S″ '
                         f'正常归档 → 收尾完成 = true；落点 {winner.rid if winner else "无"}，'
                         f'非「待重定义」死路')
    else:
        expect('S7', False, '§6.7 收尾继任面缺「放弃且留有继任者（新建替代）」形态——'
                            'S″ 正常归档后不被认作收尾对象，组合表待重定义行条件（尾端异常）'
                            '又不命中，唯一出口退化为报告阻塞（红）')

    # 处置形态全集断言（复核轮新增）：替换 / 放弃-删边 / 放弃-新建替代 /
    # 类型 1 补建 / 类型 5 补建——每个形态都必须解析出收尾对象或重定义出口。
    # 这是「修与验不共享位点枚举」的机械化：形态清单驱动，不按被点名的位点数。
    forms_ok = {}
    # 替换：§6.7 替换继任句 + S1
    forms_ok['替换'] = dele['§6.7替换继任句'][0] and any(
        s['scenario'] == 'S1' and s['ok'] for s in out)
    # 放弃-删边：§6.7 重定义句（含删边变体限定）+ S2
    forms_ok['放弃-删边'] = dele['§6.7无继任者重定义句'][0] and any(
        s['scenario'] == 'S2' and s['ok'] for s in out)
    # 放弃-新建替代：§6.7 新建替代继任句 + S7
    forms_ok['放弃-新建替代'] = s67_alt_ok and any(
        s['scenario'] == 'S7' and s['ok'] for s in out)
    # 类型 1 补建：§7.7 P 分支建新 P + S4
    forms_ok['类型 1 补建'] = dele['类型1_P分支'][0] and any(
        s['scenario'] == 'S4' and s['ok'] for s in out)
    # 类型 5 补建：§7.7 类型 5 补建分支 + 守卫位点
    forms_ok['类型 5 补建'] = dele['类型5唯一源'][0] and guards_ok
    missing = [f for f in DISPOSITION_FORMS if not forms_ok.get(f)]
    expect('S8_处置形态全集', not missing,
           f'五形态 = { {f: bool(forms_ok.get(f)) for f in DISPOSITION_FORMS} }；'
           f'缺出口形态: {missing or "无"}')
    return out


# ---------------------------------------------------------------------------
# 历史缺陷变异（「有牙」证据：改回缺陷形态必须被抓红）。
# 变异清单以 MUTATIONS 列表为唯一源；本段注释与 spec 注册块一律不写数目（防账目漂移）。
# ---------------------------------------------------------------------------

def run_mutation(name, text=None):
    """返回 (detected, detail)。detected=True 表示门在变异形态下变红（检出）。

    text：注入的文档文本（不覆写真实文件）；缺省读真实主稿。测试必须传 text，
    不得写真实文档。
    """
    if text is None:
        text = MAIN_DOC.read_text(encoding='utf-8')
    comp = Doc.load(COMP_DOC)
    if name == 'M1_v41_predicate':
        rows = build_rows(mutations={name})
        base_rows = build_rows()
        flipped = []
        for values in itertools.product(*[vals for _, vals in AXES]):
            c = dict(zip([n for n, _ in AXES], values))
            if (c['status'] == '已归档' and c['ledger'] == '异常'
                    and c['succ'] == '指向已建' and c['down'] == '无下游指向'):
                # 替换/新建替代/类型 1-P 正常完成后重启：字段谓词判终态、不重入类型 5
                _, w0 = resolve_cell(base_rows, c)
                _, w1 = resolve_cell(rows, c)
                if w0 and w1 and w0.rid != 'F2c' and w1.rid == 'F2c':
                    flipped.append(w0.rid)
        reds, _ = run_grid(rows)
        detected = bool(flipped)
        return detected, (f'M1: 已归档+异常+指向已建+下游不指向（替换正常完成后重启，'
                          f'§7.4 判终态不重入类型 5）落点由 {sorted(set(flipped))} 改判 '
                          f'F2c 类型 5（{len(flipped)} 格翻转，v41 假阳性复现）；'
                          f'变异态红格 {len(reds)}')
    if name == 'M2_v48_family2':
        bad = text.replace('**建边 / 返工加边**（两端都在活动区时建立的边）',
                           '**建边**（两端都在活动区时建立的边）')
        if bad == text:
            return False, 'M2: 变异文本未命中（定位失败）'
        d2 = Doc(bad)
        dele = build_delegations(d2, comp)
        detected = not dele['族2成员'][0]
        return detected, (f'M2: 族 2 成员删「返工加边」后 族2成员 委派解析失败（红={detected}）')
    if name == 'M3_terminal_guard':
        bad = text.replace('最后归档旧任务（已归档者不重复归档）；**项目层任务 P**',
                          '最后归档旧任务；**项目层任务 P**', 1)
        if bad == text:
            return False, 'M3: 变异文本未命中（定位失败）'
        d2 = Doc(bad)
        sites = type5_guard_sites(d2)
        detected = len(sites) != 4 or not all(v >= 1 for v in sites.values())
        return detected, f'M3: 类型 5 守卫位点 {sites} 不满足 4/4（红={detected}）'
    if name == 'M4_f1':
        # 把 §6.7 收尾继任面改回「替换或放弃均由人重新定义」（E1 前形态）→ S1 必须红
        bad = text.replace(
            '收尾任务被替换、或被放弃且留有继任者（新建替代）时，继任者即收尾对象（替换由人按新范围'
            '细化其收尾内容）、被放弃且无继任者（删边变体）时由人重新定义收尾任务；',
            '收尾任务自身被替换或放弃时，由人重新定义收尾任务；')
        if bad == text:
            return False, 'M4: 变异文本未命中（E1/R1 尚未应用或文本已漂移）'
        d2 = Doc(bad)
        dele = build_delegations(d2, comp)
        detected = not (dele['§6.7替换继任句'][0] and dele['§6.7新建替代继任句'][0]
                        and dele['§6.7无继任者重定义句'][0])
        return detected, f'M4: §6.7 回退旧句后 S1/S7 收尾继任面解析红={detected}'
    if name == 'M6_newalt_relay':
        # 删掉「留有继任者（新建替代）」半句 → 放弃-新建替代形态失去继任规则 → S7/S8 必红
        bad = text.replace(
            '收尾任务被替换、或被放弃且留有继任者（新建替代）时，继任者即收尾对象（替换由人按新范围'
            '细化其收尾内容）、被放弃且无继任者（删边变体）时由人重新定义收尾任务；',
            '收尾任务被替换时继任者即收尾对象（由人按新范围细化其收尾内容）、'
            '被放弃且无继任者（删边变体）时由人重新定义收尾任务；')
        if bad == text:
            return False, 'M6: 变异文本未命中（R1 尚未应用或文本已漂移）'
        d2 = Doc(bad)
        dele = build_delegations(d2, comp)
        detected = not dele['§6.7新建替代继任句'][0]
        return detected, (f'M6: §6.7 删「留有继任者（新建替代）」半句后，S7 新建替代继任面与 '
                          f'S8 处置形态全集（放弃-新建替代缺出口）解析红={detected}')
    if name == 'M7_doc_predicate_text':
        # 只改文档、不改模型：把 §7.4 表行终态枝改回 v41 旧措辞（「替换指向为空」作
        # 终态必要条件）→ 委派「§7.4继任者枝」「§7.4终态枝」必须解析失败。
        # 锁 M1 的检出边界：M1 是模型内变异（base-vs-mutant 翻转），看不到
        # 「文档谓词被改、模型未跟改」的漂移；本变异补上这一面。
        old_pred = ('**处分已到终态**（已归档，且未归档下游已不指向它，'
                    '且（无替换指向 或 继任者已建））')
        new_pred = ('**处分已到终态**（已归档，且未归档下游已不指向它，'
                    '且替换指向为空）')
        bad = text.replace(old_pred, new_pred)
        if bad == text:
            return False, 'M7: 变异文本未命中（§7.4 终态枝措辞已漂移）'
        d2 = Doc(bad)
        dele = build_delegations(d2, comp)
        detected = not (dele['§7.4继任者枝'][0] and dele['§7.4终态枝'][0])
        return detected, (f'M7: §7.4 文本改回 v41 旧谓词后，终态枝/继任者枝委派解析红={detected}'
                          f'（文档谓词漂移、模型未跟改时静态门必须红）')
    if name == 'M5_rowcount':
        lines = text.split('\n')
        idx = [i for i, l in enumerate(lines)
               if l.startswith('| 无当前任务，P 存在且未归档，前置全部正常，账本为“无记录” | 只执行 P |')]
        if not idx:
            return False, 'M5: 定位失败（未收尾表「只执行 P」行）'
        bad = '\n'.join(lines[:idx[0]] + lines[idx[0] + 1:])
        d2, t2 = parse_main(bad)
        detected = t2['未收尾'] != EXPECTED_TABLES['未收尾']
        return detected, (f'M5: 删一行后文档实测未收尾 {t2["未收尾"]} ≠ 已编码 '
                          f'{EXPECTED_TABLES["未收尾"]}（红={detected}）')
    raise SystemExit(f'未知变异: {name}')


MUTATIONS = ['M1_v41_predicate', 'M2_v48_family2', 'M3_terminal_guard', 'M4_f1',
             'M5_rowcount', 'M6_newalt_relay', 'M7_doc_predicate_text']


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

CURRENT_DOC, CURRENT_TABLES = parse_main()


def cmd_check(as_json=False):
    rows = build_rows()
    dele = build_delegations(CURRENT_DOC)
    reds, stats = run_grid(rows)
    errs = check_delegations(rows, dele, CURRENT_TABLES)
    scen = run_scenarios(rows, CURRENT_DOC, dele)
    scen_red = [s for s in scen if not s['ok']]
    stats = dict(stats, unresolved=stats['unresolved'] + len(errs))
    ok = not reds and not errs and not scen_red
    if as_json:
        print(json.dumps({'result': 'D1 GREEN' if ok else 'D1 RED', 'grid': stats,
                          'red_cells': [{'cell': c, 'problems': p} for c, p in reds],
                          'errors': errs, 'scenarios': scen,
                          'tables': CURRENT_TABLES}, ensure_ascii=False, indent=1))
        return 0 if ok else 1
    for c, p in reds[:20]:
        print(f'RED cell {c}: ' + '; '.join(p))
    if len(reds) > 20:
        print(f'... 共 {len(reds)} 个红格')
    for e in errs:
        print('ERR', e)
    for s in scen_red:
        print(f'RED scenario {s["scenario"]}: {s["detail"]}')
    print(f'grid: combos={stats["combos"]} red={stats["red"]} dup={stats["dup"]} '
          f'unresolved={stats["unresolved"]}')
    print('D1 GREEN' if ok else 'D1 RED')
    return 0 if ok else 1


def cmd_grid(as_json=False):
    rows = build_rows()
    if as_json:
        out = []
        for values in itertools.product(*[vals for _, vals in AXES]):
            c = dict(zip([n for n, _ in AXES], values))
            _, w = resolve_cell(rows, c)
            out.append({' | '.join(values): w.rid if w else 'RED'})
        print(json.dumps(out, ensure_ascii=False))
    else:
        print('axes\t' + '\t'.join(n for n, _ in AXES) + '\trow')
        for values in itertools.product(*[vals for _, vals in AXES]):
            c = dict(zip([n for n, _ in AXES], values))
            _, w = resolve_cell(rows, c)
            print('\t'.join(values) + '\t' + (w.rid if w else 'RED'))
    return 0


def cmd_scenarios(as_json=False):
    rows = build_rows()
    dele = build_delegations(CURRENT_DOC)
    scen = run_scenarios(rows, CURRENT_DOC, dele)
    if as_json:
        print(json.dumps(scen, ensure_ascii=False, indent=1))
    else:
        for s in scen:
            print(f'{"OK " if s["ok"] else "RED"} {s["scenario"]}: {s["detail"]}')
    return 0 if all(s['ok'] for s in scen) else 1


def cmd_mutate(names, as_json=False):
    results = []
    for n in names:
        detected, detail = run_mutation(n)
        results.append({'mutation': n, 'detected': detected, 'detail': detail})
        if not as_json:
            print(f'{"DETECTED" if detected else "MISSED "} {n}: {detail}')
    ok = all(r['detected'] for r in results)
    if as_json:
        print(json.dumps({'all_detected': ok, 'results': results}, ensure_ascii=False, indent=1))
    else:
        print(f'mutations: {sum(r["detected"] for r in results)}/{len(results)} detected')
        print('D1 MUTATE OK' if ok else 'D1 MUTATE RED')
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description='D1 状态枚举门（v50 收口批次）')
    ap.add_argument('--check', action='store_true', help='跑全部检查（默认）')
    ap.add_argument('--grid', action='store_true', help='打印全网格判定表（tsv）')
    ap.add_argument('--scenarios', action='store_true', help='跑全部链级结构场景')
    ap.add_argument('--mutate', help='应用变异并断言被检出：NAME|ALL')
    ap.add_argument('--json', action='store_true', help='机器可读输出')
    a = ap.parse_args(argv)
    if a.mutate:
        return cmd_mutate(MUTATIONS if a.mutate == 'ALL' else [a.mutate], a.json)
    if a.grid:
        return cmd_grid(a.json)
    if a.scenarios:
        return cmd_scenarios(a.json)
    return cmd_check(a.json)


if __name__ == '__main__':
    sys.exit(main())
