#!/usr/bin/env python3
"""Migrated r68/r71 field variants retain rejection and no-false-verdict checks."""
import json

from scripts.tests.wf_review.test_report_input_single_source import ImportHarness, payload, review
from scripts.tests.wf_review.test_review_coverage import DecideHarness, AXES, records


class ReportVariantTest(ImportHarness):
    def assert_rejected_without_verdict(self, body):
        path = self.write(body)
        with self.assertRaises(review.ReviewError) as caught:
            self.import_report(path)
        self.assertEqual(caught.exception.code, 'WF_REVIEW_INVALID')
        task = json.loads((self.task_dir / 'task.json').read_text())
        reviews = task.get('reviews') or {}
        self.assertIsNone(reviews.get('result'))
        self.assertFalse(any(a.get('outcome') == 'fail' for a in reviews.get('attempts') or []))

    def test_r71_invalid_axis_variants_never_write_a_verdict(self):
        valid = dict(payload()['axes'])
        missing = dict(valid)
        missing.pop('testability')
        for label, axes in (('empty', {}), ('only', {'range': 'pass'}),
                            ('missing', missing), ('unknown', dict(valid, extra='pass'))):
            with self.subTest(variant=label):
                self.assert_rejected_without_verdict(payload(axes=axes))

    def test_r68_invalid_report_inputs_are_rejected_before_verdict(self):
        axes = dict(payload()['axes'], testability={'conclusion': 'fail', 'basis': 'missing'})
        for label, body in (
                ('blocking', payload(findings=[{'id': 'F1', 'severity': 'blocker', 'summary': 'blocking'}])),
                ('undeclared-cli', payload(**{'source-cli': 'gemini'})),
                ('empty-scope', payload(**{'read-scope': []})),
                ('fail-without-evidence', payload(axes=axes))):
            with self.subTest(variant=label):
                self.assert_rejected_without_verdict(body)


class LegacyScopeExceptionTest(DecideHarness):
    def test_r68_legacy_scope_exceptions_do_not_block_valid_review(self):
        self.stage(AXES)
        task_path = self.task_dir / 'task.json'
        task = json.loads(task_path.read_text())
        for imported in task['reviews']['imported']:
            path = self.root / imported['report_path']
            text = path.read_text()
            text = text.replace('"findings": []', '"scope-exceptions": ["legacy note"], "findings": []')
            path.write_text(text)
            imported['report_digest'] = records.file_digest(path)
        records.write_json(task_path, task)
        self.decide()
        saved = json.loads(task_path.read_text())
        self.assertEqual(saved['reviews']['result']['verdict'], 'pass')
