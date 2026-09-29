"""Regression checks for lifecycle guarantees and safe scaffolding."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]

def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

CHECK = load('check-plans')
SCAFFOLD = load('scaffold-plan')

class Plans(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / 'example'
        SCAFFOLD.populate(self.directory, 'example', 'Example', ['build', 'design', 'delivery'], True, schema_version=2)
        self.data = json.loads((self.directory / 'plan.json').read_text())
        self.validator = Draft202012Validator(json.loads((ROOT / 'assets/plan.schema.json').read_text()), format_checker=FormatChecker())

    def errors(self):
        (self.directory / 'plan.json').write_text(json.dumps(self.data))
        return CHECK.validate(self.directory, self.validator)

    def run_phases(self):
        self.data.update(status='active', activePhases=['00','01'])
        for p in self.data['phases'][:2]:
            p['status']='active'

    def test_parallel_and_partial_block(self):
        self.run_phases()
        self.assertEqual(self.errors(), [])
        self.data['phases'][0]['status']='blocked'
        self.assertEqual(self.errors(), [])
        self.data['phases'][1]['status']='blocked'
        self.assertTrue(self.errors())
        self.data['status']='blocked'
        self.assertEqual(self.errors(), [])

    def test_declared_dependency_required(self):
        self.run_phases()
        self.data['phases'][1]['dependsOn']=['00']
        self.assertTrue(self.errors())
        self.data['phases'][0].update(status='complete', evidence=['verified commit'])
        self.data['activePhases']=['01']
        self.assertEqual(self.errors(), [])

    def test_running_list_and_invalid_dependencies(self):
        self.run_phases()
        self.data['activePhases']=['00']
        self.assertTrue(self.errors())
        self.data.update(status='draft', activePhases=[])
        for p in self.data['phases']: p['status']='pending'
        for dep in ['00', '02', '99']:
            self.data['phases'][0]['dependsOn']=[dep]
            self.assertTrue(self.errors())

    def test_baseline_draft_evidence(self):
        self.data['baseline']=[{'title':'Skeleton','evidence':['Health check passed at commit abc']}]
        self.assertEqual(self.errors(), [])
        self.data['baseline'][0]['evidence']=[]
        self.assertTrue(self.errors())

    def test_outline_promotion(self):
        p=self.data['phases'][2]
        p['type']='outline'
        (self.directory / p['document']).write_text((ROOT / 'assets/outline-phase.md').read_text())
        self.assertEqual(self.errors(), [])
        self.data.update(status='active', activePhases=['02'])
        p['status']='active'
        self.assertTrue(self.errors())
        p['type']='full'
        self.assertTrue(self.errors())
        (self.directory / p['document']).write_text((ROOT / 'assets/_template/PHASE-00-foundation.md').read_text())
        self.assertEqual(self.errors(), [])

    def test_completion_and_legacy_sequential(self):
        self.data['phases'][0]['status']='complete'
        self.assertTrue(self.errors())
        self.data['phases'][0]['evidence']=['actual check']
        self.data.update(schemaVersion=1, activePhase=None)
        del self.data['activePhases']; del self.data['baseline']
        self.assertTrue(self.errors()) # draft cannot contain completed phases
        self.data.update(status='active', activePhase='02')
        self.data['phases'][2]['status']='active'
        self.assertTrue(self.errors()) # pending 01 prevents 02 in v1
        self.data['phases'][1].update(status='complete', evidence=['actual check'])
        self.assertEqual(self.errors(), [])

    def test_terminal_states_and_completion_evidence(self):
        self.data['status']='complete'
        self.assertTrue(self.errors())
        for p in self.data['phases']:
            p.update(status='complete', evidence=['Recorded check and artifact'])
        self.assertEqual(self.errors(), [])
        self.data['phases'][2]['type']='outline'
        self.assertTrue(self.errors())
        self.data['phases'][2].update(type='full', status='pending', evidence=[])
        self.data['status']='shelved'
        self.assertEqual(self.errors(), [])
        self.data['phases'][2]['status']='blocked'
        self.data['activePhases']=['02']
        self.assertTrue(self.errors())

    def test_incompatible_schema_writes_nothing(self):
        plans=Path(self.temp.name)/'PLANS'
        plans.mkdir()
        schema=json.loads((ROOT/'assets/plan.schema.json').read_text())
        schema['properties']['schemaVersion']={'const':1}
        schema_file=plans/'plan.schema.json'
        original=json.dumps(schema)
        schema_file.write_text(original)
        cmd=[sys.executable,str(ROOT/'scripts/scaffold-plan.py'),'new-plan','--root',self.temp.name,'--schema-version','2']
        result=subprocess.run(cmd,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertFalse((plans/'new-plan').exists())
        self.assertEqual(schema_file.read_text(),original)

    def scaffold_cli(self, *options):
        return subprocess.run(
            [sys.executable, str(ROOT/'scripts/scaffold-plan.py'), 'new-plan',
             '--root', self.temp.name, *options], capture_output=True, text=True)

    def test_default_fresh_repo_is_v1(self):
        result=self.scaffold_cli('--phase', 'build', '--phase', 'delivery')
        self.assertEqual(result.returncode, 0, result.stderr)
        data=json.loads((Path(self.temp.name)/'PLANS/new-plan/plan.json').read_text())
        self.assertEqual(data['schemaVersion'], 1)
        self.assertIsNone(data['activePhase'])
        self.assertNotIn('activePhases', data)
        self.assertNotIn('baseline', data)
        self.assertNotIn('type', data['phases'][0])
        self.assertEqual(data['phases'][1]['dependsOn'], ['00'])

    def install_real_v1_schema(self):
        plans=Path(self.temp.name)/'PLANS'
        plans.mkdir()
        original=(ROOT/'tests/fixtures/v1-plan.schema.json').read_bytes()
        (plans/'plan.schema.json').write_bytes(original)
        return plans, original

    def test_default_real_v1_schema_succeeds(self):
        plans, original=self.install_real_v1_schema()
        result=self.scaffold_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        data=json.loads((plans/'new-plan/plan.json').read_text())
        self.assertEqual(data['schemaVersion'], 1)
        self.assertIsNone(data['activePhase'])
        self.assertEqual((plans/'plan.schema.json').read_bytes(), original)

    def test_explicit_v2_fresh_repo(self):
        result=self.scaffold_cli('--schema-version', '2')
        self.assertEqual(result.returncode, 0, result.stderr)
        data=json.loads((Path(self.temp.name)/'PLANS/new-plan/plan.json').read_text())
        self.assertEqual(data['schemaVersion'], 2)
        self.assertEqual(data['activePhases'], [])
        self.assertNotIn('activePhase', data)

    def test_explicit_v2_real_v1_schema_fails_without_writes(self):
        plans, original=self.install_real_v1_schema()
        result=self.scaffold_cli('--schema-version', '2')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('rejected the version 2 plan', result.stderr)
        self.assertIn('review and merge version 2 support', result.stderr)
        self.assertIn('validate existing plans', result.stderr)
        self.assertEqual(list(plans.iterdir()), [plans/'plan.schema.json'])
        self.assertEqual((plans/'plan.schema.json').read_bytes(), original)

    def test_v2_flags_require_explicit_opt_in(self):
        for options in [('--independent',), ('--outline', 'foundation'),
                        ('--schema-version', '1', '--independent')]:
            with self.subTest(options=options):
                result=self.scaffold_cli(*options)
                self.assertEqual(result.returncode, 2)
                self.assertIn('require explicit --schema-version 2', result.stderr)
                self.assertFalse((Path(self.temp.name)/'PLANS').exists())

    def test_cli_scaffold_and_refuse_overwrite(self):
        cmd=[sys.executable,str(ROOT/'scripts/scaffold-plan.py'),'cli-plan','--root',self.temp.name,'--phase','build','--phase','design','--schema-version','2','--independent','--outline','design']
        result=subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        d=json.loads((Path(self.temp.name)/'PLANS/cli-plan/plan.json').read_text())
        self.assertEqual(d['phases'][1]['dependsOn'],[])
        self.assertEqual(d['phases'][1]['type'],'outline')
        self.assertNotEqual(subprocess.run(cmd,capture_output=True).returncode,0)



class SliceExecution(unittest.TestCase):
    """execution.mode slices: phases run through an epic slice."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / 'PLANS' / 'example'
        self.directory.parent.mkdir()
        SCAFFOLD.populate(self.directory, 'example', 'Example', ['build', 'ship'], execution='slices')
        self.data = json.loads((self.directory / 'plan.json').read_text())
        self.validator = Draft202012Validator(json.loads((ROOT / 'assets/plan.schema.json').read_text()), format_checker=FormatChecker())
        self.epic = self.root / '.devops/slices/001-x-phase-build/slice.json'
        self.epic.parent.mkdir(parents=True)
        self.write_epic('epic-slice', 'in_progress')

    def write_epic(self, slice_type, status):
        self.epic.write_text(json.dumps({'sliceType': slice_type, 'status': status}))

    def errors(self):
        (self.directory / 'plan.json').write_text(json.dumps(self.data))
        return CHECK.validate(self.directory, self.validator, self.root)

    def start_first_phase(self, with_epic=True):
        self.data.update(status='active', activePhase='00')
        self.data['phases'][0]['status'] = 'active'
        if with_epic:
            self.data['phases'][0]['epicSlice'] = '.devops/slices/001-x-phase-build/slice.json'

    def test_scaffold_is_valid_and_uses_planned_slices(self):
        self.assertEqual(self.data['execution']['mode'], 'slices')
        self.assertEqual(self.errors(), [])
        text = (self.directory / 'PHASE-00-build.md').read_text()
        self.assertIn('## Planned slices', text)
        self.assertNotIn('## Implementation steps', text)

    def test_slice_mode_rejects_implementation_steps_heading(self):
        doc = self.directory / 'PHASE-00-build.md'
        doc.write_text(doc.read_text().replace('## Planned slices', '## Implementation steps'))
        self.assertTrue(any('Planned slices' in e for e in self.errors()))

    def test_active_phase_needs_an_epic_slice(self):
        self.start_first_phase(with_epic=False)
        self.assertTrue(any('requires epicSlice' in e for e in self.errors()))
        self.start_first_phase()
        self.assertEqual(self.errors(), [])

    def test_epic_slice_must_exist_and_be_an_epic(self):
        self.start_first_phase()
        self.write_epic('feature-slice', 'in_progress')
        self.assertTrue(any('epic-slice' in e for e in self.errors()))
        self.write_epic('epic-slice', 'in_progress')
        self.data['phases'][0]['epicSlice'] = '.devops/slices/missing/slice.json'
        self.assertTrue(any('existing regular file' in e for e in self.errors()))
        self.data['phases'][0]['epicSlice'] = '../outside/slice.json'
        self.assertTrue(self.errors())

    def test_complete_phase_needs_a_done_epic(self):
        self.start_first_phase()
        self.data['phases'][0].update(status='complete', evidence=['Epic slice closed; child slices linked'])
        self.data.update(status='shelved', activePhase=None)
        self.assertTrue(any('to be done' in e for e in self.errors()))
        self.write_epic('epic-slice', 'done')
        self.assertEqual(self.errors(), [])

    def test_closed_epic_cannot_back_a_running_phase(self):
        self.start_first_phase()
        self.write_epic('epic-slice', 'done')
        self.assertTrue(any('complete or re-plan' in e for e in self.errors()))

    def test_epic_slice_paths_are_unique_and_mode_gated(self):
        self.start_first_phase()
        self.data['phases'][1]['epicSlice'] = self.data['phases'][0]['epicSlice']
        self.assertTrue(any('unique' in e for e in self.errors()))
        del self.data['execution']
        self.data['phases'][1].pop('epicSlice')
        self.assertTrue(any('requires execution.mode slices' in e for e in self.errors()))

    def test_scaffold_cli_flag_and_incompatible_schema(self):
        cmd = [sys.executable, str(ROOT / 'scripts/scaffold-plan.py'), 'cli-plan', '--root', self.temp.name, '--execution', 'slices']
        self.assertEqual(subprocess.run(cmd, capture_output=True, text=True).returncode, 0)
        schema = json.loads((ROOT / 'assets/plan.schema.json').read_text())
        del schema['properties']['execution']
        (self.root / 'PLANS/plan.schema.json').write_text(json.dumps(schema))
        result = subprocess.run(cmd[:2] + ['other-plan'] + cmd[3:], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('does not support execution.mode slices', result.stderr)
        self.assertFalse((self.root / 'PLANS/other-plan').exists())

if __name__ == '__main__': unittest.main()
