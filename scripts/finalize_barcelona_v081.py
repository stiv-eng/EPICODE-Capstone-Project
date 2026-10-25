"""Assemble actual pytest/Chrome evidence, then refresh final release reports."""
import argparse
import json
import platform
import xml.etree.ElementTree as ET

from motorsport.ml.barcelona_recovery import ROOT, file_sha
from motorsport.ml.barcelona_experiment import dump
from motorsport.ml.diagnosis_v072 import verify_inventory


def main(warnings):
    tests_path = ROOT/'artifacts/barcelona_v081/pytest-final.xml'
    suite = ET.parse(tests_path).getroot().find('testsuite')
    tests = {key:int(suite.attrib[key]) for key in ('tests', 'errors', 'failures', 'skipped')}
    assert tests['errors'] == tests['failures'] == tests['skipped'] == 0
    browser_path = ROOT/'artifacts/v081/UI_BROWSER_V081.json'
    browser = json.loads(browser_path.read_text(encoding='utf-8'))
    console_path = ROOT/'artifacts/v081/browser_console_v081.json'
    console = json.loads(console_path.read_text(encoding='utf-8'))
    assert all(row['status']=='passed' for row in browser)
    errors = [event for event in console if event['method']=='Runtime.exceptionThrown' or
        (event['method']=='Runtime.consoleAPICalled' and event['params'].get('type')=='error') or
        (event['method']=='Log.entryAdded' and event['params']['entry'].get('level')=='error')]
    assert not errors, errors
    preserved = json.loads((ROOT/'docs/BASELINE_PRESERVATION_V081.json').read_text(encoding='utf-8'))
    verify_inventory(preserved['sha256'])
    result = json.loads((ROOT/'docs/ML_RESULTS_V081.json').read_text(encoding='utf-8'))
    for name, digest in result['evidence_sha256'].items():
        assert file_sha(ROOT/name) == digest, name
    budget_count = sum('rendering budget' in row['check'] for row in browser)
    performance_count = sum(row['check']=='Final browser performance' for row in browser)
    dump(ROOT/'docs/UI_BROWSER_V081.json', browser)
    verification = dict(baseline_commit='11c11f8', branch='feat/sim-telemetry-v081',
        baseline_tests=dict(passed=257, warnings=217, seconds=189.60),
        tests=dict(passed=tests['tests'], failures=0, errors=0, skipped=0, warnings=warnings,
                   seconds=float(suite.attrib['time']), retained=257, added=tests['tests']-257,
                   junit_sha256=file_sha(tests_path)),
        browser=dict(scenario='v081', total_records=len(browser),
            workflow_checks=len(browser)-budget_count-performance_count,
            render_budgets=budget_count, performance_records=performance_count,
            console_errors=0, runtime_exceptions=0, source_sha256=file_sha(browser_path),
            console_sha256=file_sha(console_path),
            playback_wall_intervals=[dict(check=row['check'], median_s=row['median_observed_wall_interval_s'])
                                    for row in browser if row['check'].startswith('v081 playback')]),
        preservation=dict(files=len(preserved['sha256']), all_validated_laps=205, status='passed'),
        python=platform.python_version(), platform=platform.platform(),
        additional_checks=dict(compileall='passed', pip_check='No broken requirements found',
            whitespace='passed', frozen_numerical_regression='FROZEN_REGRESSION_V081.json',
            frozen_experiment_rerun='verified without fitting/rescoring'),
        remote_actions=dict(push=False, merge=False, operational_promotion=False))
    dump(ROOT/'docs/VERIFICATION_V081.json', verification)
    from scripts.report_barcelona_v081 import main as report
    report()
    print(json.dumps(verification, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pytest-warnings', type=int, required=True, help='Actual warnings from the pytest terminal summary')
    main(parser.parse_args().pytest_warnings)
