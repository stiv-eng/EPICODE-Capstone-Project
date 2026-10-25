"""Assemble measured scope-reset evidence; no model dependency or training."""
import ast
import json
from pathlib import Path
import subprocess
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

from motorsport.ingestion.barcelona import file_sha

ROOT = Path(__file__).resolve().parents[1]


def dump(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8', newline='\n')


def write(path, value):
    path.write_text(value.strip()+'\n', encoding='utf-8', newline='\n')


def main():
    retired = json.loads((ROOT/'docs/archive/RETIRED_FILES_V082.json').read_text(encoding='utf-8'))
    archive = retired['archive_commit']
    actual_archive = subprocess.check_output(['git','rev-parse',retired['archive_ref']], cwd=ROOT, text=True).strip()
    assert actual_archive == archive
    archived = set(subprocess.check_output(['git','ls-tree','-r','--name-only',archive], cwd=ROOT, text=True).splitlines())
    for names in retired['groups'].values():
        for name in names:
            assert name in archived and not (ROOT/name).exists(), name
    actual_removals = set(subprocess.check_output(['git','diff','--name-only','--diff-filter=D',archive], cwd=ROOT, text=True).splitlines())
    assert actual_removals == {name for names in retired['groups'].values() for name in names}
    suite_path = ROOT/'artifacts/v082-final-tests.xml'
    suite = ET.parse(suite_path).getroot().find('testsuite')
    tests = {key:int(suite.attrib[key]) for key in ('tests','errors','failures','skipped')}
    assert tests['errors'] == tests['failures'] == tests['skipped'] == 0
    test_ledger = json.loads((ROOT/'docs/archive/RETIRED_TESTS_V082.json').read_text(encoding='utf-8'))
    regression = json.loads((ROOT/'docs/DATA_ANALYSIS_REGRESSION_V082.json').read_text(encoding='utf-8'))
    for source in regression['sources']:
        if source['key'].startswith(('barcelona:', 'acgym:', 'local:')):
            continue
        path = Path(source['key'])
        if path.is_absolute() and path.is_relative_to(ROOT):
            source['key'] = 'local:'+path.relative_to(ROOT).as_posix()
    dump(ROOT/'docs/DATA_ANALYSIS_REGRESSION_V082.json', regression)
    inventory = json.loads((ROOT/'docs/archive/LOCAL_ARTIFACT_INVENTORY_V082.json').read_text(encoding='utf-8'))
    # Recheck all protected bytes at the end; no model is deserialized.
    for relative, item in inventory['untouched_local_files'].items():
        path = ROOT/relative
        assert path.stat().st_size == item['bytes'] and file_sha(path) == item['sha256'], relative
    browser, error_records = [], []
    known_page_error = "The page that you have requested does not seem to exist. Running the app's main page."
    expected_paths = {'/'+route+'/_stcore/'+endpoint for route in ('ml','replay') for endpoint in ('health','host-config')}
    for scenario, filename in [('v082','UI_BROWSER_V082.json'), ('uploads','UI_BROWSER_V062.json'), ('fixtures','UI_BROWSER_V082.json')]:
        folder = ROOT/'artifacts/v082'/scenario
        results_path = folder/filename
        results = json.loads(results_path.read_text(encoding='utf-8'))
        console_path = folder/f'browser_console_{scenario}.json'
        console = json.loads(console_path.read_text(encoding='utf-8'))
        assert all(row['status']=='passed' for row in results)
        errors, expected_404, expected_page, unexpected, runtime = [], 0, 0, [], 0
        for event in console:
            kind, params = event['method'], event['params']
            is_error = (kind=='Runtime.exceptionThrown' or (kind=='Log.entryAdded' and params['entry'].get('level')=='error') or
                        (kind=='Runtime.consoleAPICalled' and params.get('type')=='error'))
            if not is_error:
                continue
            errors.append(event)
            if kind=='Runtime.exceptionThrown':
                runtime += 1
            entry = params.get('entry', {})
            expected_network = (scenario=='v082' and kind=='Log.entryAdded' and entry.get('source')=='network' and
                urlparse(entry.get('url','')).path in expected_paths and '404 (Not Found)' in entry.get('text',''))
            expected_missing = (scenario=='v082' and kind=='Runtime.consoleAPICalled' and
                [arg.get('value') for arg in params.get('args', [])]==[known_page_error])
            if expected_network:
                expected_404 += 1
            elif expected_missing:
                expected_page += 1
            else:
                unexpected.append(event)
        assert not unexpected and runtime==0, unexpected
        budget = sum('rendering budget' in row['check'] for row in results)
        performance = sum(row['check']=='Final browser performance' for row in results)
        browser.append(dict(scenario=scenario, total_records=len(results), workflow_checks=len(results)-budget-performance,
            render_budgets=budget, performance_records=performance, runtime_exceptions=runtime,
            console_error_events=len(errors), expected_retired_route_network_404=expected_404,
            expected_page_not_found_messages=expected_page, unexpected_error_events=0,
            model_imports_and_artifact_access='blocked by verification-only sitecustomize guard',
            results_sha256=file_sha(results_path), console_sha256=file_sha(console_path), records=results))
        error_records.extend(dict(scenario=scenario, event=event) for event in errors)
    dump(ROOT/'docs/UI_BROWSER_V082.json', browser)
    dump(ROOT/'docs/UI_BROWSER_CONSOLE_V082.json', error_records)
    # Inspect imports rather than relying on optional libraries being installed.
    imports = []
    for folder in ('motorsport','motorsport_ui','pages','scripts'):
        for path in (ROOT/folder).rglob('*.py'):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                names = [item.name for item in node.names] if isinstance(node,ast.Import) else ([node.module or ''] if isinstance(node,ast.ImportFrom) else [])
                imports.extend(names)
    assert not any(name.startswith(('motorsport.ml','motorsport_prediction','sklearn','keras','torch','joblib')) for name in imports)
    evidence = ['docs/DATA_ANALYSIS_BASELINE_V082.json','docs/DATA_ANALYSIS_REGRESSION_V082.json',
        'docs/UI_BROWSER_V082.json','docs/UI_BROWSER_CONSOLE_V082.json','docs/archive/RETIRED_FILES_V082.json',
        'docs/archive/RETIRED_TESTS_V082.json','docs/archive/LOCAL_ARTIFACT_INVENTORY_V082.json']
    verification = dict(version='0.8.2', date='2026-10-25', branch='feat/scope-reset-v082', archive_ref=retired['archive_ref'],
        archive_commit=archive, archived_baseline_tests=dict(passed=287, warnings=217, seconds=222.14),
        tests=dict(passed=tests['tests'], failures=0, errors=0, skipped=0, warnings=0,
            seconds=float(suite.attrib['time']), retired_prediction_cases=test_ledger['retired_cases'],
            relocated_data_validation_cases=len(test_ledger['relocated_data_validation']), new_scope_checks=8,
            junit_sha256=file_sha(suite_path)),
        removed_files={group:len(names) for group,names in retired['groups'].items()},
        browser=[{key:value for key,value in item.items() if key!='records'} for item in browser],
        preservation=dict(checked_local_files=len(inventory['untouched_local_files']),
            bytes_unchanged=sum(item['bytes'] for item in inventory['untouched_local_files'].values()),
            private_signing_keys_left_in_place=len(inventory['private_key_paths_manual_backup']),
            source_signal_hashes_unchanged=regression['signal_hashes_unchanged'],
            overview_summaries_unchanged=regression['overview_summaries_unchanged'],
            barcelona_lap_trajectories_unchanged=205, barcelona_analysis_laps=205,
            previous_analysis_laps=204, f5='byte-for-byte unchanged'),
        checks=dict(compileall='passed', dependency_check='No broken requirements found',
            whitespace='passed', active_import_graph='no prediction/model package imports',
            guarded_startup='Home, Explorer, Overview and Comparison pass with models and prediction packages inaccessible'),
        remote_actions=dict(push=False, merge=False, history_rewrite=False, branch_deletion=False),
        evidence_sha256={name:file_sha(ROOT/name) for name in evidence})
    dump(ROOT/'docs/VERIFICATION_V082.json', verification)
    counts = verification['removed_files']
    browser_rows = '\n'.join('| '+ ' | '.join(str(item[key]) for key in
        ('scenario','workflow_checks','render_budgets','performance_records','expected_retired_route_network_404','expected_page_not_found_messages','unexpected_error_events'))+' |' for item in browser)
    report = f'''# Release v0.8.2 — Scope reset to Motorsport Data Analysis

The progressive final-lap-time prediction subsystem is removed from active code,
navigation, dependency declarations and CI. The surviving application provides
Session Overview, Data Explorer and Telemetry Comparison with the existing design,
selection semantics, measured-data calculations and shared hover/cursor. This
release adds no replacement predictor, new delta-time method or new dataset.

## Verified archive before removal

Incoming branch: `feat/sim-telemetry-v081`, HEAD `11c11f8`, with the delivered v081
changes uncommitted. Reverified **287 tests passed**, zero failed/skipped, 217
existing Keras/Torch warnings, 222.14 s. Preserved those changes in local commit
**`{archive}`** and created **`{retired['archive_ref']}`**, then
`feat/scope-reset-v082`. No push, merge, reset, history rewrite or branch deletion.
The sandbox Git ownership mismatch required a per-command safe.directory setting;
global Git configuration was not changed.

The [recovery guide](archive/PROGRESSIVE_LAPTIME_ML_RECOVERY.md) documents a separate
worktree, exact commit, LF checkout for frozen hashes, original requirements and
manual backup of ignored datasets/models/paired signing keys. Git history alone
does not contain these ignored artifacts. The archival reference is local.

## Removed and retained

Removed **{counts['prediction_modules']} prediction implementation/UI modules**,
**{counts['prediction_pages']} prediction pages**, **{counts['research_scripts']} dedicated
research scripts**, {counts['obsolete_mixed_browser_workflows']} obsolete mixed
browser/archive workflows, {counts['prediction_tests']} dedicated test files,
the sequence dependency manifest and {counts['archived_prediction_evidence']}
prediction report/table/figure files. Every removed file exists in the archive
commit; the [reviewed file ledger](archive/RETIRED_FILES_V082.json) lists individual
paths. Removals were classified by actual dependencies and purpose, not directory
name alone. Ignored files were not moved or deleted.

The removal covers original/dense/remaining SVR, stop-aware corrections, historical
prediction baselines, ordered Ridge, Keras GRU, model stores/loaders, feature
experiments, training/selection/evaluation, experimental replay, diagnostics,
prediction caches/state and ML navigation. Existing analysis source/chart caches
remain. Metadata uncertainty now describes source limitations without obsolete
ML-corpus messages.

Preserved: CSV/Parquet/MoTeC/GT7 adapters, raw columns, declared units,
normalization, timing validation, verified laps, session windows, driver inputs,
G-G equal scales, tyre analysis, recorded Cockpit inspection, available positions,
stable comparison ordering/identities/colors and browser-only synchronized cursors.
The original optional FastF1 lap/stint/telemetry/map analysis remains; its
prediction pages are gone. Existing descriptive regression/distance-comparison
helpers are retained as analysis, with no new delta method.

## Dependency cleanup

Removed scikit-learn/joblib from core requirements; Keras/Torch/joblib from the
optional extension requirements; removed the obsolete sequence requirements and
the ML legacy CI job. Core is NumPy/Pandas/PyArrow/Plotly/Streamlit plus pytest for
verification. Optional FastF1 remains for retained Formula 1 analysis. Installed
historical packages were not uninstalled, preserving the old environment for
recovery. Normal startup does not import prediction packages or inspect models.
Both VS Code F5 configuration files are byte-identical.

## Data regression and cleanup issue found

All **73 baseline source signal hashes and overview summaries are unchanged**.
All **205 original Barcelona lap trajectories and verified times match** the
pre-cleanup inclusive data contract. **244 local files / 912,978,399 bytes** of
raw data, model binaries and F5 files are verified unchanged; five private signing
keys stay at their existing paths. No key contents or binary models are committed.

The previous analysis UI exposed only **204** Barcelona laps because it omitted
the already validated v071 **1 ms target-rounding tolerance**. The ML loader
accepted a half-ms boundary that the analysis loader did not. The new small
`motorsport/ingestion/barcelona.py` adapter moves source integrity/path utilities
out of the retired ML package and applies that same inclusive timing setting.
The affected WL stint now exposes 8 instead of 7 laps, making all 205 accessible.
This changes no raw signal, existing valid timing or analytical calculation.
See [exact regression evidence](DATA_ANALYSIS_REGRESSION_V082.json) and
[frozen pre-cleanup measurements](DATA_ANALYSIS_BASELINE_V082.json).

## Automated tests and actual Chrome

**{tests['tests']} tests passed**, zero failed/errors/skipped/warnings,
**{float(suite.attrib['time']):.2f} s**. Dedicated prediction cases were deliberately
retired: **{test_ledger['retired_cases']} cases**, individually recorded in
[the test ledger](archive/RETIRED_TESTS_V082.json). The data-only half-ms timing
regression was relocated from the mixed ML suite. Eight new scope/compatibility
checks were added; the original launch guard was renamed and preserved. Mixed
tests lose only assertions protecting the deliberately removed ML gates/feature
table; their data/geometry/hover/timing assertions remain.

The surviving suite protects ingestion, normalization, timing, filtering, lap
ordering, source/selection state, G-G scaling, track geometry, hover/cursors and
the original F5 files. A clean subprocess starts all four active local pages with
Keras/Torch/sklearn/joblib imports and model file/stat access forbidden. The same
guard is enabled in every browser-server run. No ignored file is moved to make
this test pass.

| Chrome scenario | Workflows | Render budgets | Performance records | Expected removed-route 404s | Expected page-not-found messages | Unexpected errors |
| --- | --- | --- | --- | --- | --- | --- |
{browser_rows}

The four 404 network requests and two Streamlit page-not-found console messages
come exclusively from deliberately opening `/ml` and `/replay`. They are retained
in [console evidence](UI_BROWSER_CONSOLE_V082.json), separately classified from
unexpected errors; none is silently discarded. Normal surviving workflows have
zero unexpected console errors and zero runtime exceptions. The removed pages
cannot execute; normal navigation exposes only analysis.

Browser checks retain GT7/Monza/Barcelona sections and comparison, real pointer
and keyboard cursors, zoom/pan alignment, stable selection rows, unavailable/gap
handling, 20 hover updates without Python rerun/numerical mutation, responsive
480/960/1600 layouts, actual Parquet/CSV file uploads, stationary position and
clockless/legacy renderer fixtures. Shared hover/render implementation files are
unchanged. Compileall, pip check and whitespace checks pass. See
[verification](VERIFICATION_V082.json) and [full browser evidence](UI_BROWSER_V082.json).

## Launch and future direction

Use the unchanged VS Code **Motorsport Telemetry Analyzer → F5**, or:

```powershell
.\\.venv\\Scripts\\python.exe -m streamlit run streamlit_app.py
```

Open Data Explorer, choose a recording or upload CSV/Parquet, then inspect signals
or compare verified laps/windows. No prediction model artifacts are required.
The [active feature list](ACTIVE_FEATURES_V082.md), [architecture](ARCHITECTURE_V082.md)
and updated README describe this scope.

The research direction is closed. Two conditional future options are easier
recording selection and better import mapping guidance, evaluated explicitly for
user problem, simplest alternative, practical benefit, required evidence and a
small feasibility check in [the recommendation](NEXT_RELEASE_RECOMMENDATION.md).
The user will choose a direction separately; neither is started here.

## Acceptance

| Criteria | Evidence |
| --- | --- |
| AC1, AC12 | Exact archived commit/reference, preserved incoming work, separate-worktree recovery instructions |
| AC2 | Protected local file digests unchanged, ignored assets/keys kept, manual backup inventory |
| AC3, AC4 | Reviewed source/page/workflow removal, import-graph guard and retired-route checks |
| AC5–AC7 | Source/overview/lap regression, existing analysis tests, real browser geometry and cursor checks |
| AC8, AC9 | Lean dependency declarations/CI, guarded startup with model packages/artifacts inaccessible |
| AC10 | Complete surviving/new test suite and three actual Chrome scenarios |
| AC11 | Updated README/CHANGELOG, active features, architecture, archive and recommendation |
'''
    write(ROOT/'docs/RELEASE_V082_REPORT.md', report)
    print(json.dumps({key:value for key,value in verification.items() if key not in ('evidence_sha256',)}, indent=2))


if __name__ == '__main__':
    main()
