"""One-off evidence harness: tester emulates the unimplemented mechanism.

Native task lifecycle calls are real; dependency decisions are test predicates.
This is not a mechanism implementation or evidence of production integration.
"""
from pathlib import Path
import io
import json
import os
import shutil
import subprocess
import tarfile

PYTHON = '/softwares/python/bin/python3'
EVIDENCE = Path(__file__).resolve().parent
SEED = Path('/tmp/dep-mech-chain-20261026')
BASELINE = 'bd39e6d'
PREFIX = Path('/tmp/dep-mech-chain-20261026-v43-replay-run3')
EVENTS = []
RESULTS = {}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


class Fixture:
    def __init__(self, root, fresh=True):
        self.root = Path(root)
        self.env = dict(os.environ, TRELLIS_CONTEXT_ID='v43-' + self.root.name)
        if fresh:
            assert not self.root.exists(), f'Refuse to replace existing fixture: {root}'
            self.root.mkdir()
            data = subprocess.check_output(['git', '-C', str(SEED), 'archive', BASELINE])
            with tarfile.open(fileobj=io.BytesIO(data)) as archive:
                archive.extractall(self.root, filter='data')
            self.run(['git', 'init', '-b', 'fixture'])
            (self.root / '.git/info').mkdir(exist_ok=True)
            (self.root / '.git/info/exclude').write_text('.trellis/.runtime/\n')
            self.run(['git', 'config', 'user.name', 'Workflow Fixture Tester'])
            self.run(['git', 'config', 'user.email', 'fixture@example.invalid'])
            (self.root / '.trellis/.developer').write_text('name=xzc\n')
            self.run(['git', 'add', '.'])
            self.run(['git', 'commit', '-m', 'fixture: original Trellis baseline bd39e6d'])
            self.run(['git', 'branch', 'main'])
            self.tasks = {}
            self.ledger = {}
            write_json(self.root / '.dep/project.json', {
                'handoff_complete': True,
                'note': 'Test input: new project, no legacy suspended items; tester confirms handoff applicability.',
            })
            self.persist('fixture: confirmed project-level handoff fact')
        else:
            self.tasks = self.read_committed('.dep/tasks.json')
            self.ledger = self.read_committed('.dep/ledger.json')

    def run(self, args, expected=0):
        r = subprocess.run(args, cwd=self.root, env=self.env, capture_output=True, text=True)
        EVENTS.append({'root': str(self.root), 'command': args, 'rc': r.returncode,
                       'stdout': r.stdout, 'stderr': r.stderr})
        write_json(EVIDENCE / 'chain-commands.json', EVENTS)
        assert r.returncode == expected, (args, r.returncode, r.stdout, r.stderr)
        return r.stdout

    def native(self, *args, expected=0):
        return self.run([PYTHON, '.trellis/scripts/task.py', *args], expected)

    def read_committed(self, path):
        return json.loads(self.run(['git', 'show', 'HEAD:' + path]))

    def persist(self, label):
        write_json(self.root / '.dep/tasks.json', self.tasks)
        write_json(self.root / '.dep/ledger.json', self.ledger)
        write_json(self.root / '.dep/view.json', {
            'nodes': list(self.tasks),
            'prerequisites': {i: t['deps'] for i, t in self.tasks.items()},
            'ready': [i for i, t in self.tasks.items() if not self.archived(i)
                      and i not in self.ledger and all(self.normal(d) for d in t['deps'])],
        })
        paths = ['.dep', '.trellis/tasks']
        if (self.root / 'docs').exists():
            paths.append('docs')
        self.run(['git', 'add', '--', *paths])
        self.run(['git', 'commit', '-m', label])
        assert self.read_committed('.dep/tasks.json') == self.tasks
        assert self.read_committed('.dep/ledger.json') == self.ledger

    def locate(self, identity):
        paths = [p for p in (self.root / '.trellis/tasks').rglob('task.json')
                 if p.parent.name == self.tasks[identity]['dir']]
        assert len(paths) == 1, (identity, paths)
        return paths[0].parent

    def archived(self, identity):
        return 'archive' in self.locate(identity).relative_to(self.root / '.trellis/tasks').parts

    def normal(self, identity):
        return self.archived(identity) and self.ledger.get(identity, {}).get('status') == 'normal'

    def registration(self, identity):
        note = self.ledger.get(identity, {}).get('note')
        return note.get('registration') if isinstance(note, dict) else None

    def available(self, identity, expected_dir=None, source=None):
        if identity in self.tasks and self.tasks[identity]['dir'] != expected_dir:
            return False
        if identity in self.ledger and identity not in self.tasks:
            return False
        for owner, value in self.ledger.items():
            registration = self.registration(owner)
            claim = value.get('replaced_by') == identity or (registration and registration['id'] == identity)
            if claim and owner != source:
                return False
        return True

    def create(self, identity, slug, deps=(), origin=None, source=None):
        assert self.available(identity, source=source), ('type4 occupancy', identity)
        self.native('create', slug, '--slug', slug, '--base-branch', 'main',
                    '--description', 'First-batch chain fixture: ' + slug)
        candidates = [p for p in (self.root / '.trellis/tasks').glob('*/task.json')
                      if json.loads(p.read_text()).get('id') == slug]
        assert len(candidates) == 1
        self.tasks[identity] = {'dir': candidates[0].parent.name, 'deps': list(deps),
                                'origin': origin, 'created': len(self.tasks) + 1}
        return candidates[0].parent

    def start(self, identity):
        self.native('start', '--allow-empty-context', self.tasks[identity]['dir'])

    def finish_normal(self, identity, label):
        assert identity not in self.ledger and all(self.normal(x) for x in self.tasks[identity]['deps'])
        self.start(identity)
        self.native('archive', self.tasks[identity]['dir'])
        assert self.archived(identity)
        self.ledger[identity] = {'status': 'normal', 'note': '', 'replaced_by': None}
        self.persist(label)

    def prepare(self, target, rid, slug, label):
        assert not self.archived(target) and not self.registration(target)
        assert self.ledger.get(target, {}).get('status') in (None, 'suspended')
        assert self.available(rid), ('type4 occupancy', rid)
        before = self.ledger.get(target, {}).get('status', 'unrecorded')
        self.ledger[target] = {'status': 'suspended', 'replaced_by': None,
                               'note': {'registration': {'id': rid, 'locator': slug, 'before': before}}}
        self.persist(label)

    def publish(self, target, label):
        marker = self.read_committed('.dep/ledger.json')[target]['note']['registration']
        inherited = self.read_committed('.dep/tasks.json')[target]['deps'].copy()
        self.create(marker['id'], marker['locator'], inherited, target, source=target)
        self.tasks[target]['deps'].append(marker['id'])
        self.ledger[target]['note'] = ''
        self.persist(label)
        assert marker['id'] not in self.tasks[marker['id']]['deps']

    def clearable(self, target):
        project = self.read_committed('.dep/project.json')
        members = [i for i, t in self.tasks.items() if t.get('origin') == target]
        return (project.get('handoff_complete') is True and not self.archived(target)
                and self.ledger.get(target, {}).get('status') == 'suspended'
                and not self.registration(target) and bool(members)
                and all(self.archived(i) for i in members)
                and all(self.normal(i) for i in self.tasks[target]['deps']))

    def clear(self, target, label):
        assert self.clearable(target)
        del self.ledger[target]
        self.persist(label)

    def begin_replace(self, old, new, label):
        assert not self.archived(old) and self.available(new)
        assert self.ledger.get(old, {}).get('status') in (None, 'suspended')
        self.ledger[old] = {'status': 'abnormal', 'note': 'Tester input: replacement approved', 'replaced_by': new}
        self.persist(label)
        self.native('finish')

    def finish_replace(self, old, slug, label):
        new = self.ledger[old]['replaced_by']
        assert self.available(new, source=old), ('type4 occupancy', new)
        inherited = self.read_committed('.dep/tasks.json')[old]['deps'].copy()
        self.create(new, slug, inherited, self.tasks[old]['origin'], source=old)
        for identity, task in self.tasks.items():
            if old in task['deps'] and not self.archived(identity):
                task['deps'] = [new if dep == old else dep for dep in task['deps']]
        self.persist(label + ': build and reconnect')
        assert not self.archived(old), 'Build/reconnect must precede old archive'
        self.native('archive', self.tasks[old]['dir'])
        assert self.terminal(old)

    def terminal(self, old):
        successor = self.ledger[old].get('replaced_by')
        return (self.archived(old) and (not successor or successor in self.tasks)
                and not any(old in task['deps'] for identity, task in self.tasks.items()
                            if not self.archived(identity)))

    def audit(self, label):
        assert len(set(t['dir'] for t in self.tasks.values())) == len(self.tasks)
        observed = {}
        for identity, task in self.tasks.items():
            path = self.locate(identity)
            observed[identity] = str(path.relative_to(self.root))
            assert all(dep in self.tasks and dep != identity for dep in task['deps'])
            assert task['origin'] is None or task['origin'] in self.tasks
            assert not self.registration(identity)
            if self.archived(identity):
                assert self.ledger[identity]['status'] in ('normal', 'abnormal')
            if self.ledger.get(identity, {}).get('status') == 'normal':
                assert self.archived(identity) and all(self.normal(i) for i in task['deps'])
            pointer = self.ledger.get(identity, {}).get('replaced_by')
            if pointer:
                assert pointer != identity and pointer in self.tasks and self.terminal(identity)
                assert self.tasks[pointer]['deps'] == task['deps']
        native = [p.parent.name for p in (self.root / '.trellis/tasks').rglob('task.json')
                  if p.parent.name != '00-bootstrap-guidelines']
        assert set(native) == set(t['dir'] for t in self.tasks.values()) and len(native) == len(self.tasks)
        def visit(identity, trail):
            assert identity not in trail, ('cycle', trail, identity)
            for dep in self.tasks[identity]['deps']:
                visit(dep, trail | {identity})
        for identity in self.tasks:
            visit(identity, set())
        assert self.run(['git', 'status', '--porcelain']) == ''
        snapshot = {'fixture': str(self.root), 'head': self.run(['git', 'rev-parse', 'HEAD']).strip(),
                    'tasks': self.tasks, 'ledger': self.ledger, 'native_paths': observed, 'identity_errors': []}
        write_json(EVIDENCE / (label + '.json'), snapshot)
        return snapshot


def passed(number, detail, fixture):
    RESULTS[number] = {'result': 'PASS', 'detail': detail, 'fixture': str(fixture.root),
                       'head': fixture.run(['git', 'rev-parse', 'HEAD']).strip()}
    write_json(EVIDENCE / 'chain-results.json', RESULTS)
    print(number, 'PASS:', detail, flush=True)


def replay():
    f = Fixture(PREFIX)
    for identity, slug, deps in [('100', 'proj-p', []), ('101', 't1', ['100']),
                                  ('102', 't2', ['101']), ('103', 't3', ['102']),
                                  ('104', 'wrapup', ['103'])]:
        f.create(identity, slug, deps)
    write_json(f.root / 'docs/baseline.json', {'scope': 'first-batch fixture', 'excluded': 'second batch',
               'acceptance': 'chain and identity checks', 'architecture': 'Trellis native plus emulated dependency records',
               'external_dependencies': 'seed bd39e6d', 'rollback': 'isolated fixture', 'spec': 'docs/spec.md'})
    (f.root / 'docs/spec.md').write_text('# Fixture spec\nSee baseline.json for scope and acceptance.\n')
    f.persist('S1: baseline and initial task graph')
    f.finish_normal('100', 'S1: P normal after native archive')
    assert f.normal('100') and all(f.normal(x) for x in f.tasks['101']['deps'])
    passed('S1', 'Native P lifecycle; baseline and graph persisted; T1 ready.', f)
    f.finish_normal('101', 'S2: T1 normal after native archive')
    f.start('102')
    passed('S2', 'Native T1 start/archive; T2 starts only after T1 normal.', f)
    f.prepare('102', '105', 'r1t2fix', 'S3: prepare R1 and suspension in one commit')
    f.publish('102', 'S3: publish R1 identity, origin, inherited deps and target edge')
    before = f.run(['git', 'status', '--porcelain'])
    assert f.ledger['102']['status'] == 'suspended'
    rejected_finish = f.ledger.get('102', {}).get('status') != None
    rejected_rework = f.archived('101')
    assert rejected_finish and rejected_rework
    assert f.run(['git', 'status', '--porcelain']) == before == ''
    passed('S7', 'Emulated source guards reject suspended finish and archived rework; zero writes.', f)
    f.finish_normal('105', 'S3: R1 normal')
    f.clear('102', 'S3: clear target suspension by full step-5 predicate')
    passed('S3', 'Prepare/create/publish/execute/clear completed; R1 has no self-edge.', f)
    f.prepare('102', '106', 'r2t2fix', 'S4: second registration prepared, before R2 creation')
    restarted = Fixture(PREFIX, fresh=False)
    assert restarted.registration('102')['id'] == '106' and '106' not in restarted.tasks
    assert restarted.normal('105') and not restarted.clearable('102')
    f = restarted
    f.publish('102', 'S4: recover second registration using same prewritten 106')
    f.finish_normal('106', 'S4: R2 normal')
    passed('S4', 'Restart reads committed marker despite historical R1 completion; R2=106 recovered.', f)
    f.native('finish')
    f.native('current', expected=1)
    assert f.clearable('102') and f.ledger['102']['status'] == 'suspended'
    f.clear('102', 'S8: empty pointer reaches stage 2 and clears suspension')
    f.start('102')
    passed('S8', 'Native pointer empty/current rc1; after global exclusions stage2 clears T2.', f)
    assert not f.available('106', source='102')
    assert f.available('107', source='102')
    f.begin_replace('102', '107', 'S5: unique successor107 prewritten with abnormal state')
    copy_root = Path(str(PREFIX) + '-s6')
    assert not copy_root.exists()
    shutil.copytree(f.root, copy_root)
    f.finish_replace('102', 't2v2', 'S5')
    f.audit('final-main')
    passed('S5', 'Replacement uses free107; R2=106 retained; all inherited deps and downstream updated.', f)
    interrupted = Fixture(copy_root, fresh=False)
    assert interrupted.ledger['102']['replaced_by'] == '107' and '107' not in interrupted.tasks
    assert not interrupted.terminal('102') and not interrupted.archived('102')
    interrupted.finish_replace('102', 't2v2', 'S6: type5 recovery')
    interrupted.audit('final-s6')
    passed('S6', 'Restart sees prewritten107 with missing successor; build/reconnect precede archive; terminal stable.', interrupted)
    p = Fixture(Path(str(PREFIX) + '-p'))
    p.create('200', 'p')
    p.create('201', 't1', ['200'])
    p.create('202', 't2', ['200'])
    p.persist('S9: initial P and downstream')
    p.start('200')
    p.begin_replace('200', '203', 'S9: unique P successor203 prewritten')
    p.finish_replace('200', 'p2', 'S9')
    p.start('203')
    assert p.terminal('200') and not p.archived('203')
    assert p.ledger['200']['replaced_by'] == '203'
    passed('S9', 'P resolves along established200->203; project remains unclosed and continues successor P.', p)
    p.start('201')
    assert not p.archived('201') and not p.archived('202') and p.ledger.get('202') is None
    assert p.tasks['202']['deps'] == ['203'] and '201' not in p.tasks['202']['deps']
    p.tasks['201']['deps'].append('202')
    p.persist('S10a: add active prerequisite202 to in-progress201')
    assert json.loads((p.locate('201') / 'task.json').read_text())['status'] == 'in_progress'
    assert not all(p.normal(i) for i in p.tasks['201']['deps'])
    state = p.run(['git', 'status', '--porcelain'])
    assert p.archived('200')  # Proposed edge to200 rejected before any write.
    assert p.run(['git', 'status', '--porcelain']) == state == ''
    p.audit('final-p')
    passed('S10', 'Real201 continues in_progress; emulated finish guard blocks; archived200 edge rejected without writes.', p)
    assert set(RESULTS) == {'S' + str(i) for i in range(1, 11)}
    print('10/10 PASS; final-main, final-s6, final-p identity_errors=[]', flush=True)


if __name__ == '__main__':
    replay()
