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
        SCAFFOLD.populate(self.directory, 'example', 'Example', ['build', 'design', 'delivery'], True)
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
        cmd=[sys.executable,str(ROOT/'scripts/scaffold-plan.py'),'new-plan','--root',self.temp.name]
        result=subprocess.run(cmd,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertFalse((plans/'new-plan').exists())
        self.assertEqual(schema_file.read_text(),original)

    def test_cli_scaffold_and_refuse_overwrite(self):
        cmd=[sys.executable,str(ROOT/'scripts/scaffold-plan.py'),'cli-plan','--root',self.temp.name,'--phase','build','--phase','design','--independent','--outline','design']
        result=subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        d=json.loads((Path(self.temp.name)/'PLANS/cli-plan/plan.json').read_text())
        self.assertEqual(d['phases'][1]['dependsOn'],[])
        self.assertEqual(d['phases'][1]['type'],'outline')
        self.assertNotEqual(subprocess.run(cmd,capture_output=True).returncode,0)

if __name__ == '__main__': unittest.main()
