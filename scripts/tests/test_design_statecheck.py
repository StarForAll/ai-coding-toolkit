#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/tests/test_design_statecheck.py — D1 门的单元测试。

覆盖：网格四断言（命中唯一 / 出口非空 / 委派可落地 / 不重复）、链级结构场景、
全部变异检出、元断言（表行数三方比对）、CLI 入口退出码、src 注释自检、
变异文本注入（不触真实文件）。清单数目以脚本内列表为唯一源，注释不写数目。
标准库 unittest；不写文件（变异在注入文本上进行）。
"""
import importlib.util
import itertools
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO / 'scripts' / 'design-statecheck.py'
spec = importlib.util.spec_from_file_location('design_statecheck', SCRIPT)
dsc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dsc)


class GridTests(unittest.TestCase):
    def setUp(self):
        self.rows = dsc.build_rows()
        self.dele = dsc.build_delegations(dsc.CURRENT_DOC)
        self.tables = dsc.CURRENT_TABLES

    def test_grid_all_green(self):
        reds, stats = dsc.run_grid(self.rows)
        self.assertEqual(stats, {'combos': 25920, 'red': 0, 'dup': 0, 'unresolved': 0},
                         msg=f'red cells: {reds[:5]}')

    def test_combos_total(self):
        total = 1
        for _, vals in dsc.AXES:
            total *= len(vals)
        self.assertEqual(total, 25920)

    def test_disposition_forms_complete(self):
        self.assertEqual(dsc.DISPOSITION_FORMS,
                         ['替换', '放弃-删边', '放弃-新建替代', '类型 1 补建', '类型 5 补建'])

    def test_every_row_has_src_and_exit(self):
        errs = dsc.check_delegations(self.rows, self.dele, self.tables)
        self.assertEqual(errs, [])

    def test_expected_tables_match_document(self):
        for name, exp in dsc.EXPECTED_TABLES.items():
            self.assertEqual(self.tables[name], exp, msg=f'{name} 行数漂移')

    def test_no_exit_is_block_only(self):
        for r in self.rows:
            if 'redirect' in r.flags:
                continue
            flat = '；'.join(r.actions)
            if '报告阻塞' in flat:
                self.assertTrue(any(k in flat for k in
                                    ('递归', '自检', '对账', '重定义', '等前置', '取', '开工')),
                                msg=f'{r.rid} 报告阻塞无向前动作兜底')

    def test_no_mutex_actions(self):
        # 互斥断言：任一行不得同时携带 clear_suspend 与 may_block
        for r in self.rows:
            has_clear = 'clear_suspend' in r.flags
            has_block = 'may_block' in r.flags
            self.assertFalse(has_clear and has_block, msg=f'{r.rid} 互斥动作并存')

    def test_clear_and_block_not_co_present(self):
        for r in self.rows:
            has_clear = 'clear_suspend' in r.flags
            has_block = 'may_block' in r.flags
            self.assertFalse(has_clear and has_block, msg=f'{r.rid} 互斥动作并存')

    def test_redirect_rows_do_not_exclusive(self):
        for r in self.rows:
            if 'redirect' in r.flags:
                # 转发行必须与同段至少一行并存（否则该格会 0 命中）
                siblings = [x for x in self.rows
                            if x.seg == r.seg and x.rid != r.rid and 'redirect' not in x.flags]
                self.assertTrue(siblings, msg=f'{r.rid} 无并存落点行')

    def test_pointer_axioms(self):
        # §3 推导公理抽样：全轴组合下 eff_pointer 与文档口径一致
        for values in itertools.product(*[vals for _, vals in dsc.AXES]):
            c = dict(zip([n for n, _ in dsc.AXES], values))
            if c['pointer'] == '无':
                self.assertEqual(dsc.eff_pointer(c), '无')
            elif c['status'] == '已归档' or c['ledger'] in ('正常', '异常'):
                self.assertEqual(dsc.eff_pointer(c), '无效')

    def test_seg3_recovery_gate(self):
        # 第三段输入闸门：已归档+无记录/挂起（类型 1）不得进第三段
        c = dsc.make_cell(status='已归档', ledger='无记录')
        self.assertFalse(dsc.seg3_input_recovered(c))
        c = dsc.make_cell(status='已归档', ledger='挂起')
        self.assertFalse(dsc.seg3_input_recovered(c))


class ScenarioTests(unittest.TestCase):
    def setUp(self):
        self.rows = dsc.build_rows()
        self.scen = dsc.run_scenarios(self.rows, dsc.CURRENT_DOC,
                                      dsc.build_delegations(dsc.CURRENT_DOC))

    def test_all_scenarios_green(self):
        reds = [s for s in self.scen if not s['ok']]
        self.assertEqual(reds, [], msg=str(reds))

    def test_s1_lands_c4_not_block(self):
        s1 = [s for s in self.scen if s['scenario'] == 'S1'][0]
        self.assertTrue(s1['ok'])
        self.assertIn('非报告阻塞', s1['detail'])
        self.assertIn('C4', s1['detail'])

    def test_s2_lands_redefine(self):
        s2 = [s for s in self.scen if s['scenario'] == 'S2'][0]
        self.assertIn('重定义', s2['detail'])

    def test_s5_chain(self):
        s5 = [s for s in self.scen if s['scenario'] == 'S5'][0]
        for step in ('→H3', '→H1', '→H2'):
            self.assertIn(step, s5['detail'])


class MutationTests(unittest.TestCase):
    def test_m1_predicate_flip_detected(self):
        detected, detail = dsc.run_mutation('M1_v41_predicate')
        self.assertTrue(detected, msg=detail)
        self.assertIn('v41 假阳性复现', detail)

    def test_m2_family2_detected(self):
        detected, detail = dsc.run_mutation('M2_v48_family2')
        self.assertTrue(detected, msg=detail)

    def test_m3_guard_detected(self):
        detected, detail = dsc.run_mutation('M3_terminal_guard')
        self.assertTrue(detected, msg=detail)

    def test_m4_f1_detected(self):
        detected, detail = dsc.run_mutation('M4_f1')
        self.assertTrue(detected, msg=detail)

    def test_m5_rowcount_detected(self):
        detected, detail = dsc.run_mutation('M5_rowcount')
        self.assertTrue(detected, msg=detail)

    def test_m6_newalt_relay_detected(self):
        detected, detail = dsc.run_mutation('M6_newalt_relay')
        self.assertTrue(detected, msg=detail)

    def test_m7_doc_predicate_text_detected(self):
        # M1 的检出边界锁：只改文档 §7.4 终态枝措辞、模型不跟改 → 静态门必须红
        detected, detail = dsc.run_mutation('M7_doc_predicate_text')
        self.assertTrue(detected, msg=detail)

    def test_all_mutations_detected_list_driven(self):
        # 清单驱动的全量回归：不手写变异名/数目，以 MUTATIONS 为唯一源
        for name in dsc.MUTATIONS:
            with self.subTest(mutation=name):
                detected, detail = dsc.run_mutation(name)
                self.assertTrue(detected, msg=detail)

    def test_no_stale_enumeration_comments(self):
        # 账目层守卫：脚本与测试内不得出现会随清单增长过期的数字区间注释
        # （清单以 MUTATIONS / run_scenarios 的 expect 调用为唯一源）。
        # 被禁串在守卫内部以拼接构造，避免守卫自身命中。
        src_script = Path(dsc.__file__).read_text(encoding='utf-8')
        src_test = Path(__file__).read_text(encoding='utf-8')
        bads = ['M1' + '–M' + '5', 'S1' + '–S' + '6', str(5) + ' 个历史缺陷变异']
        for bad in bads:
            self.assertNotIn(bad, src_script, msg=f'script 含过期枚举注释 «{bad}»')
            self.assertNotIn(bad, src_test, msg=f'test 含过期枚举注释 «{bad}»')

    def test_unknown_mutation_rejected(self):
        with self.assertRaises(SystemExit):
            dsc.run_mutation('M0_nonexistent')

    def test_mutation_uses_injected_text_not_real_file(self):
        # 复核轮修正：变异在注入文本上进行，绝不读写真实主稿。
        # 用一段「已应用 R1」的合法文本与一段占位文本分别注入，验证 M4 行为
        # 只取决于注入内容，且真实文档全程未被触碰。
        real = dsc.MAIN_DOC.read_text(encoding='utf-8')
        self.assertIn('留有继任者（新建替代）', real)  # R1 已应用
        detected, detail = dsc.run_mutation('M4_f1', text=real)
        self.assertTrue(detected)
        # 占位文本：变异串未命中 → MISSED（不抛、不写文件）
        detected2, detail2 = dsc.run_mutation('M4_f1', text='占位')
        self.assertFalse(detected2)
        self.assertIn('未命中', detail2)
        self.assertEqual(dsc.MAIN_DOC.read_text(encoding='utf-8'), real)


class CliTests(unittest.TestCase):
    def run_cli(self, *argv):
        return dsc.main(list(argv))

    def test_check_green_exit_zero(self):
        self.assertEqual(self.run_cli('--check'), 0)

    def test_mutate_all_exit_zero(self):
        self.assertEqual(self.run_cli('--mutate=ALL'), 0)

    def test_scenarios_exit_zero(self):
        self.assertEqual(self.run_cli('--scenarios'), 0)

    def test_grid_runs(self):
        # 网格输出全部组合 + 1 行表头，逐行格式 tsv；行数由轴积派生，不手写
        import io
        import contextlib
        total = 1
        for _, vals in dsc.AXES:
            total *= len(vals)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = self.run_cli('--grid')
        out = buf.getvalue().splitlines()
        self.assertEqual(rc, 0)
        self.assertEqual(len(out), total + 1)
        for line in out[1:]:
            self.assertNotIn('\tRED', line, msg=f'grid 出现红格: {line[:80]}')


class DocParseTests(unittest.TestCase):
    def test_missing_table_locating_fails(self):
        with self.assertRaises(SystemExit):
            dsc.Doc('无表格文本').table_rows('| 不存在 | 的表头 |')

    def test_missing_section_locating_fails(self):
        with self.assertRaises(SystemExit):
            dsc.Doc('无章节').section('9.9 不存在')

    def test_mutation_on_bad_text_reports_miss(self):
        # 复核轮修正：原实现用 write_text('占位') 覆写真实主稿再靠 finally 恢复，
        # Ctrl-C/OOM 即丢失未提交的 E1–R1 改动；改为注入文本，不触真实文件。
        detected, detail = dsc.run_mutation('M4_f1', text='占位')
        self.assertFalse(detected)
        self.assertIn('未命中', detail)


if __name__ == '__main__':
    unittest.main()
