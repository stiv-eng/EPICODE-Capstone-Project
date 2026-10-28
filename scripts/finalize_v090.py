"""Consolidate measured v090 verification without rewriting frozen v082 reports."""
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

from motorsport.ingestion.barcelona import file_sha

ROOT = Path(__file__).resolve().parents[1]


def dump(name, value):
    (ROOT / 'docs' / name).write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8', newline='\n')


def git(*args):
    return subprocess.check_output(['git', '-c', 'safe.directory='+ROOT.as_posix(), *args], cwd=ROOT, text=True).strip()


def main():
    suite_path=ROOT/'artifacts/v090-final-tests.xml'
    suite=ET.parse(suite_path).getroot().find('testsuite')
    counts={key:int(suite.attrib[key]) for key in ('tests','errors','failures','skipped')}
    assert counts['errors']==counts['failures']==counts['skipped']==0
    regression=json.loads((ROOT/'docs/DATA_ANALYSIS_REGRESSION_V090.json').read_text(encoding='utf-8'))
    assert regression['status']=='passed' and regression['barcelona_validated_laps']==205
    inventory=json.loads((ROOT/'docs/archive/LOCAL_ARTIFACT_INVENTORY_V082.json').read_text(encoding='utf-8'))
    for name,item in inventory['untouched_local_files'].items():
        path=ROOT/name
        assert path.stat().st_size==item['bytes'] and file_sha(path)==item['sha256'],name
    retired=json.loads((ROOT/'docs/archive/RETIRED_FILES_V082.json').read_text(encoding='utf-8'))
    assert git('rev-parse',retired['archive_ref'])==retired['archive_commit']
    assert git('rev-parse','feat/scope-reset-v082')==git('rev-parse','1e91142')
    assert git('branch','--show-current')=='feat/telemetry-lap-analysis-v090'
    for names in retired['groups'].values():
        assert all(not (ROOT/name).exists() for name in names)
    launch={name:file_sha(ROOT/name) for name in ('.vscode/launch.json','.vscode/tasks.json') if (ROOT/name).exists()}
    for name in launch:
        assert not git('diff','1e91142','--',name)
    assert not git('diff','1e91142','--','requirements.txt','requirements-extension.txt','.github')
    assert not git('diff','HEAD','--check')
    dependency_check=subprocess.check_output([sys.executable,'-m','pip','check'],cwd=ROOT,text=True).strip()
    subprocess.run([sys.executable,'-m','compileall','-q',
                    'motorsport/lap_analysis','motorsport_ui/lap_analysis_v090.py',
                    'pages/16_Telemetry_Lap_Analysis.py','scripts/finalize_v090.py',
                    'scripts/report_lap_analysis_v090.py','scripts/smoke_ui_v090.py'],cwd=ROOT,check=True)
    expected_paths={'/'+route+'/_stcore/'+endpoint for route in ('ml','replay') for endpoint in ('health','host-config')}
    known_page="The page that you have requested does not seem to exist. Running the app's main page."
    browser=[];error_records=[]
    for scenario,folder,filename in [
        ('v090','artifacts/v090/v090','UI_BROWSER_V090.json'),
        ('uploads','artifacts/v082/uploads','UI_BROWSER_V062.json'),
        ('fixtures','artifacts/v082/fixtures','UI_BROWSER_V082.json'),
    ]:
        result_path=ROOT/folder/filename
        console_path=ROOT/folder/f'browser_console_{scenario}.json'
        results=json.loads(result_path.read_text(encoding='utf-8'))
        console=json.loads(console_path.read_text(encoding='utf-8'))
        assert all(r['status']=='passed' for r in results)
        if scenario=='v090':
            assert any('unsupported original attachment' in r['check'] for r in results), 'v090 browser run incomplete'
        network=page=runtime=0;unexpected=[]
        for event in console:
            kind=event['method'];params=event['params'];entry=params.get('entry',{})
            if not (kind=='Runtime.exceptionThrown' or (kind=='Log.entryAdded' and entry.get('level')=='error') or
                    (kind=='Runtime.consoleAPICalled' and params.get('type')=='error')):
                continue
            error_records.append(dict(scenario=scenario,event=event))
            if kind=='Runtime.exceptionThrown':runtime+=1
            if (scenario=='v090' and kind=='Log.entryAdded' and entry.get('source')=='network' and
                urlparse(entry.get('url','')).path in expected_paths and '404 (Not Found)' in entry.get('text','')):
                network+=1
            elif (scenario=='v090' and kind=='Runtime.consoleAPICalled' and
                  [a.get('value') for a in params.get('args',[])]==[known_page]):page+=1
            else:unexpected.append(event)
        assert not unexpected and runtime==0,unexpected
        if scenario=='v090':assert network==4 and page==2
        budget=sum('rendering budget' in r['check'] for r in results)
        performance=sum(r['check']=='Final browser performance' for r in results)
        browser.append(dict(scenario=scenario,total_records=len(results),workflow_checks=len(results)-budget-performance,
            render_budgets=budget,performance_records=performance,expected_retired_route_404=network,
            expected_page_not_found_messages=page,unexpected_error_events=0,runtime_exceptions=runtime,
            model_imports_and_artifact_access='blocked by verification-only sitecustomize guard',
            results_sha256=file_sha(result_path),console_sha256=file_sha(console_path),records=results))
    dump('UI_BROWSER_V090.json',browser)
    dump('UI_BROWSER_CONSOLE_V090.json',error_records)
    measured=json.loads((ROOT/'docs/MEASUREMENTS_V090.json').read_text(encoding='utf-8'))
    for name,digest in measured['evidence_sha256'].items():assert file_sha(ROOT/name)==digest,name
    evidence=['docs/MEASUREMENTS_V090.json','docs/DATA_FEASIBILITY_V090.json',
              'docs/DATA_ANALYSIS_REGRESSION_V090.json','docs/UI_BROWSER_V090.json','docs/UI_BROWSER_CONSOLE_V090.json']
    implementation=[p for folder in ('motorsport/lap_analysis',) for p in (ROOT/folder).glob('*.py')]
    implementation += [ROOT/p for p in ('motorsport_ui/lap_analysis_v090.py','motorsport_ui/hover.html',
                                      'pages/16_Telemetry_Lap_Analysis.py','streamlit_app.py')]
    verification=dict(version='0.9.0',status='passed',remote_actions='none',baseline_commit=git('rev-parse','1e91142'),
        baseline_branch='feat/scope-reset-v082',development_branch=git('branch','--show-current'),
        archive_ref=retired['archive_ref'],archive_commit=retired['archive_commit'],
        tests=dict(passed=counts['tests'],seconds=float(suite.attrib['time']),errors=0,failures=0,skipped=0,
                   junit_sha256=file_sha(suite_path)),
        static_checks=dict(compileall='passed',diff_check='passed',pip_check=dependency_check,
                           dependency_manifests_and_ci_unchanged=True),
        browser=dict(total_records=sum(b['total_records'] for b in browser),unexpected_errors=0,runtime_exceptions=0,
                     scenarios=[{k:v for k,v in b.items() if k!='records'} for b in browser]),
        preservation=dict(checked_local_files=len(inventory['untouched_local_files']),
            bytes_unchanged=sum(i['bytes'] for i in inventory['untouched_local_files'].values()),
            original_signal_sources=regression['signal_hashes_unchanged'],
            original_barcelona_lap_trajectories=205,launch_sha256=launch,
            private_keys_left_in_place=len(inventory['private_key_paths_manual_backup'])),
        real_data=dict(cases=measured['cases'],valid=measured['valid_cases'],unavailable=measured['unavailable_cases'],
            distinct_pairs=measured['distinct_pairs'],valid_distinct_pairs=measured['valid_distinct_pairs'],
            cross_recording=measured['cross_recording']['status'],maximum_reconciliation_error_s=measured['maximum_reconciliation_error_s']),
        implementation_sha256={p.relative_to(ROOT).as_posix():file_sha(p) for p in implementation},
        evidence_sha256={p:file_sha(ROOT/p) for p in evidence})
    dump('VERIFICATION_V090.json',verification)
    print(json.dumps({k:v for k,v in verification.items() if k not in ('implementation_sha256','evidence_sha256')},indent=2))


if __name__=='__main__':main()
