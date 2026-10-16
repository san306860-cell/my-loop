"""Receipt and decision-source regressions from the methodology integration."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest

PM = Path(__file__).resolve().parent.parent / "skills" / "my-loop-pm"


class BehaviorChecks(unittest.TestCase):
    def setUp(self):
        self.index = 0
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output_dir = Path(self.temp.name)

    def case(self):
        self.index += 1
        path = self.output_dir / 'cases' / f'{self._testMethodName}-{self.index}'
        loop = path / '.my-loop'
        loop.mkdir(parents=True, exist_ok=True)
        self.state = {'phase': 'done', 'task': 'Isolated validation only', 'classification': 'simple', 'current_ticket': None, 'review_policy': {'mode': 'self', 'acceptance': ['Inspect fixture behavior']}, 'review_evidence': 'review.md'}
        self.ticket = {'id': 'T-001', 'goal': 'Isolated validation', 'status': 'done', 'acceptance': ['Inspect fixture behavior'], 'depends_on': [], 'evidence': 'receipt.md'}
        self.save(path)
        (path / 'receipt.md').write_text('Receipt fixture with an implementation location and check output.\n')
        (path / 'review.md').write_text('Review fixture, no production acceptance claim.\n')
        (loop / 'decisions.jsonl').write_text('')
        return path

    def save(self, path):
        (path / '.my-loop/state.json').write_text(json.dumps(self.state))
        (path / '.my-loop/tickets.json').write_text(json.dumps({'tickets': [self.ticket]}))

    def invoke(self, script, path):
        env = os.environ.copy()
        env['CLAUDE_PROJECT_DIR'] = str(path)
        cmd = [sys.executable, str(PM / 'hooks' / script)]
        if script == 'validate_state.py':
            cmd.append(str(path))
        result = subprocess.run(cmd, cwd=path, env=env, text=True, capture_output=True)
        return result

    def decision(self, path, **kwargs):
        row = {'id': 'D-001', 'decision': '复用当前队列', 'reason': '可逆工程选择，符合现有授权。', 'status': 'active', 'guard': {'type': 'doc', 'ref': 'brief.md'}}
        row.update(kwargs)
        (path / '.my-loop/decisions.jsonl').write_text(json.dumps(row, ensure_ascii=False) + '\n')
        return row

    def context(self, path):
        result = self.invoke('inject_decisions.py', path)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)['hookSpecificOutput']['additionalContext']

    def test_valid_relative_and_absolute_evidence(self):
        for absolute in (False, True):
            with self.subTest(absolute=absolute):
                path = self.case()
                if absolute:
                    self.ticket['evidence'] = str(path / 'receipt.md')
                    self.state['review_evidence'] = str(path / 'review.md')
                    self.save(path)
                self.assertEqual(self.invoke('validate_state.py', path).returncode, 0)

    def test_missing_ticket_receipt_is_rejected(self):
        path = self.case()
        (path / 'receipt.md').unlink()
        self.assertEqual(self.invoke('validate_state.py', path).returncode, 1)

    def test_blank_ticket_receipts_are_rejected(self):
        for content in ('', ' \n\t'):
            with self.subTest(content=repr(content)):
                path = self.case()
                (path / 'receipt.md').write_text(content)
                self.assertEqual(self.invoke('validate_state.py', path).returncode, 1)

    def test_invalid_ticket_path_types_are_rejected(self):
        for value in (True, ['receipt.md'], {'path': 'receipt.md'}, '   '):
            with self.subTest(value=value):
                path = self.case()
                self.ticket['evidence'] = value
                self.save(path)
                result = self.invoke('validate_state.py', path)
                self.assertEqual(result.returncode, 1)
                self.assertNotIn('Traceback', result.stderr)

    def test_final_review_missing_or_blank_is_rejected(self):
        for content in (None, '', '  \n'):
            with self.subTest(content=repr(content)):
                path = self.case()
                if content is None:
                    (path / 'review.md').unlink()
                else:
                    (path / 'review.md').write_text(content)
                self.assertEqual(self.invoke('validate_state.py', path).returncode, 1)

    def test_directory_and_unreadable_text_are_rejected(self):
        for name in ('receipt.md', 'review.md'):
            for kind in ('directory', 'invalid-utf8'):
                with self.subTest(name=name, kind=kind):
                    path = self.case()
                    target = path / name
                    if kind == 'directory':
                        target.unlink()
                        target.mkdir()
                    else:
                        target.write_bytes(b'\xff\xfe\xff')
                    result = self.invoke('validate_state.py', path)
                    self.assertEqual(result.returncode, 1)
                    self.assertNotIn('Traceback', result.stderr)

    def test_valid_symlink_receipt_is_supported(self):
        path = self.case()
        (path / 'receipt.md').rename(path / 'actual-receipt.md')
        (path / 'receipt.md').symlink_to(path / 'actual-receipt.md')
        self.assertEqual(self.invoke('validate_state.py', path).returncode, 0)

    def test_in_progress_task_does_not_require_completed_evidence(self):
        path = self.case()
        self.state.update(phase='build', current_ticket='T-001', review_evidence=None)
        self.ticket.update(status='working', evidence=None)
        self.save(path)
        (path / 'receipt.md').unlink()
        (path / 'review.md').unlink()
        self.assertEqual(self.invoke('validate_state.py', path).returncode, 0)

    def test_wip_and_unfinished_ticket_guards_are_preserved(self):
        path = self.case()
        self.ticket['status'] = 'working'
        self.state['current_ticket'] = 'T-001'
        self.save(path)
        self.assertEqual(self.invoke('validate_state.py', path).returncode, 1)
        self.state['phase'] = 'build'
        self.save(path)
        other = dict(self.ticket, id='T-002')
        (path / '.my-loop/tickets.json').write_text(json.dumps({'tickets': [self.ticket, other]}))
        self.assertEqual(self.invoke('validate_state.py', path).returncode, 1)

    def test_pm_source_is_preserved_without_human_approval_claim(self):
        path = self.case()
        source = 'PM：既有授权内的可逆工程选择；依据 brief.md，不是用户逐项确认。'
        self.decision(path, source=source)
        context = self.context(path)
        self.assertIn(source, context)
        self.assertNotIn('已经由人拍过板的决策', context)

    def test_source_survives_long_record_compaction(self):
        path = self.case()
        source = 'PM：工程选择｜依据 brief.md；用户未逐项确认。'
        self.decision(path, source=source, reason='需要保留但压缩时可展开查阅的详细理由。' * 600)
        context = self.context(path)
        self.assertIn(source, context)
        self.assertNotIn('需要保留但压缩时可展开查阅的详细理由。' * 100, context)
        self.assertNotIn('已经由人拍过板的决策', context)

    def test_old_source_less_decision_remains_valid_and_unknown(self):
        path = self.case()
        self.decision(path)
        self.assertEqual(self.invoke('validate_state.py', path).returncode, 0)
        context = self.context(path)
        self.assertIn('来源未知', context)
        self.assertNotIn('已经由人拍过板的决策', context)

    def test_invalid_sources_are_rejected(self):
        for source in (None, True, {}, '', '   '):
            with self.subTest(source=source):
                path = self.case()
                self.decision(path, source=source)
                self.assertEqual(self.invoke('validate_state.py', path).returncode, 1)

    def test_document_decisions_do_not_demand_tests(self):
        path = self.case()
        self.decision(path, decision='对外说明采用已确认的项目术语', source='用户：本轮已确认的词汇')
        result = self.invoke('validate_state.py', path)
        self.assertEqual(result.returncode, 0)
        self.assertNotIn('⚠', result.stdout)
        self.assertNotIn('裸奔', self.context(path))

    def test_legacy_markdown_sources_survive_compaction(self):
        for label in ('**来源**：', '来源:', '来源：'):
            with self.subTest(label=label):
                path = self.case()
                (path / '.my-loop/decisions.jsonl').unlink()
                source = 'PM 在授权内选择；依据旧项目 brief，不是用户逐项确认。'
                (path / '.my-loop/DECISIONS.md').write_text('## D-001 · 复用现有队列\n' + label + source + '\n' + '详细说明。' * 1500 + '\n')
                context = self.context(path)
                self.assertIn(source, context)
                self.assertNotIn('已经由人拍过板的决策', context)

    def test_migration_keeps_existing_data_and_validates(self):
        path = self.case()
        (path / '.my-loop/DECISIONS.md').write_text('## D-001 · 复用现有队列\n2026-10-16 · 守卫: 仅文档（brief.md）\n来源：PM 在授权内选择。\n理由：不需要新增服务。\n')
        result = self.invoke('migrate_v2.py', path)
        self.assertEqual(result.returncode, 0)
        row = json.loads((path / '.my-loop/decisions.jsonl').read_text())
        self.assertIn('PM 在授权内选择', row['reason'])
        self.assertEqual(row['guard']['type'], 'doc')
        self.assertEqual(self.invoke('validate_state.py', path).returncode, 0)
        self.assertNotIn('裸奔', result.stdout)


if __name__ == "__main__":
    unittest.main()
