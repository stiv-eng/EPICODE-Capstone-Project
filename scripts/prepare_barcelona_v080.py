"""Read-only source investigation and preservation inventory before v080 fitting."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from motorsport.ml.barcelona_recovery import ROOT, RAW, load_corpus, file_sha
from motorsport.ml.development_v072 import development_pool, group_folds
from motorsport.ml.barcelona_experiment import dump, table_write
from motorsport.ingestion.motec import read_ld


def main():
    inventory = ROOT/'docs/BASELINE_PRESERVATION_V080.json'
    if not inventory.exists():
        paths = [*ROOT.glob('docs/*V071*'), *ROOT.glob('docs/*V072*'),
                 *ROOT.glob('docs/figures/*v071.*'), *ROOT.glob('docs/figures/*v072.*'),
                 *ROOT.glob('artifacts/barcelona_v071/models/*'),
                 *ROOT.glob('artifacts/barcelona_v072/models/*'), *ROOT.glob('artifacts/models/*')]
        paths += [ROOT/p for p in ('motorsport/ml/features.py', 'motorsport/ml/inference.py',
                  'motorsport/ml/training.py', 'motorsport/ingestion/acgym_importer.py',
                  '.vscode/launch.json', '.vscode/settings.json') if (ROOT/p).exists()]
        dump(inventory, dict(baseline_commit='36b1267', initial_tests=dict(passed=233, warnings=92, seconds=157.67),
             sha256={p.relative_to(ROOT).as_posix():file_sha(p) for p in paths if p.is_file()}))
    from motorsport.ml.diagnosis_v072 import verify_inventory
    verify_inventory(json.loads(inventory.read_text(encoding='utf-8'))['sha256'])
    corpus, _ = load_corpus()
    dev = development_pool(corpus, pd.read_csv(ROOT/'docs/BARCELONA_SPLIT_V071.csv'))
    folds = group_folds(dev)
    old = pd.read_csv(ROOT/'docs/DEVELOPMENT_FOLDS_V072.csv')
    pd.testing.assert_frame_equal(folds, old)
    table_write(ROOT/'docs/DEVELOPMENT_FOLDS_V080.csv', folds)
    rows = []
    for source, labels in dev.targets.groupby('source'):
        _, channels = read_ld(RAW/source, ['Car Pos Norm', 'Session Lap Count', 'Lap Time'])
        count = np.round(channels['Session Lap Count'].values).astype(int)
        for lap in labels.itertuples(index=False):
            select = count == int(lap.source_lap)-1
            t = channels['Lap Time'].values[select]
            p = channels['Car Pos Norm'].values[select]
            finite = np.isfinite(t)&np.isfinite(p)
            t, p = t[finite], p[finite]
            d = np.diff(p)
            rows.append(dict(lap_uid=lap.lap_uid, samples=len(p), export_hz=channels['Car Pos Norm'].hz,
                declared_unit=channels['Car Pos Norm'].unit, first=p[0], last=p[-1], minimum=p.min(), maximum=p.max(),
                backward_steps=int((d < -1e-8).sum()), large_negative_steps=int((d < -.5).sum()),
                large_positive_steps=int((d > .1).sum()), max_positive_step=float(d.max()),
                max_timer_step_s=float(np.diff(t).max()), outside_unit_range=int(((p < 0)|(p > 1.001)).sum())))
    table_write(ROOT/'docs/PROGRESS_SOURCE_AUDIT_V080.csv', pd.DataFrame(rows))
    result = dict(decision='Elapsed-time fallback; percentage checkpoints disabled', laps=len(dev.laps),
        minimum=min(r['minimum'] for r in rows), maximum=max(r['maximum'] for r in rows),
        laps_with_backward_steps=sum(r['backward_steps'] > 0 for r in rows),
        laps_with_large_negative_steps=sum(r['large_negative_steps'] > 0 for r in rows),
        semantics='Position-like complete-lap endpoints are empirical evidence, not a verified ACTI mapping. Simulator NormalizedSplinePosition is documented; exact human export resampling/interpolation/latency remains unverified.',
        source_urls=['https://assetto-corsa-gym.github.io/',
          'https://proceedings.neurips.cc/paper_files/paper/2024/file/b91ea2ba1b6521940e204b7b81d5ef47-Paper-Datasets_and_Benchmarks_Track.pdf',
          'https://github.com/dasGringuen/assetto_corsa_gym/blob/main/motec_to_pickle.py',
          'https://github.com/dasGringuen/assetto_corsa_gym/blob/main/motec_to_pickle_config.yml'])
    dump(ROOT/'docs/PROGRESS_STATUS_V080.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
