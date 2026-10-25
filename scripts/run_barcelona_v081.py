"""Reproducible development-only inference measurements and one optional fit.

python -m scripts.run_barcelona_v081 --train-one-second
Each cadence runs in an isolated process for comparable peak working sets.
Existing evidence is verified/reused; no automatic repeated fitting.
"""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
import pandas as pd

from motorsport.ml.barcelona_recovery import ROOT, load_corpus, file_sha
from motorsport.ml.barcelona_experiment import dump, table_write
from motorsport.ml.dense_experiment_v080 import load_fold, working_memory
from motorsport.ml.development_v072 import development_pool, group_folds
from motorsport.ml.diagnosis_v072 import verify_inventory, pace_band
from motorsport.ml.features import FEATURES
from motorsport.ml.replay_v081 import ReplayEngine
from motorsport.ml.evaluation_v080 import metrics
from motorsport.ml.cadence_v081 import fit_one_second
from motorsport.ml.artifacts import LocalArtifactStore

OUT = ROOT/'artifacts/barcelona_v081'
RESULT = ROOT/'docs/ML_RESULTS_V081.json'


def population():
    corpus, _ = load_corpus()
    assert len(corpus.laps) == len(corpus.targets) == 205
    dev = development_pool(corpus, pd.read_csv(ROOT/'docs/BARCELONA_SPLIT_V071.csv'))
    folds = group_folds(dev)
    pd.testing.assert_frame_equal(folds, pd.read_csv(ROOT/'docs/DEVELOPMENT_FOLDS_V080.csv'))
    assert len(dev.laps) == 169 and folds.physical_session_id.nunique() == 40
    return corpus, dev, folds


def worker(cadence):
    corpus, dev, folds = population()
    evidence = json.loads((ROOT/'docs/ML_RESULTS_V080.json').read_text(encoding='utf-8'))
    assert corpus.identity == evidence['compatibility']['base_corpus_id']
    bundles = {f:load_fold(evidence['compatibility'], f)[0] for f in range(5)}
    lookup = folds.set_index('lap_uid').fold
    rows, latencies, initialization = [], [], []
    events, interrupted, max_index_bytes = [], 0, 0
    start = time.perf_counter()
    for n, source in enumerate(dev.laps):
        tick = time.perf_counter()
        fold = int(lookup[source.lap_uid])
        engine = ReplayEngine(source, bundles[fold])
        initialization.append((time.perf_counter()-tick)*1000.)
        interrupted += int(engine.index.clock_interrupted)
        max_index_bytes = max(max_index_bytes, sum(a.nbytes for group in
            (engine.index.values, engine.index.sums, engine.index.durations, engine.index.coverage) for a in group.values())+engine.index.t.nbytes)
        for nominal in engine.index.schedule(cadence):
            tick = time.perf_counter()
            row = engine.predict(nominal)
            latencies.append((time.perf_counter()-tick)*1000.)
            rows.append(dict(lap_uid=source.lap_uid, physical_session_id=source.physical_session_id,
                fold=fold, cadence_s=cadence, **{**engine.index.features(nominal), **row}))
        events.extend(dict(lap_uid=source.lap_uid, **event) for event in engine.events)
        if (n+1) % 40 == 0:
            print(f'{cadence:g}s inference: {n+1}/169 laps', flush=True)
    runtime = dict(cadence_s=cadence, snapshots=len(rows), laps=len(dev.laps),
        inference_total_s=time.perf_counter()-start, checkpoint_median_ms=float(np.median(latencies)),
        checkpoint_p95_ms=float(np.percentile(latencies, 95)), checkpoint_max_ms=float(max(latencies)),
        index_initialization_median_ms=float(np.median(initialization)),
        peak_process_working_set_bytes=working_memory(), maximum_lap_index_array_bytes=max_index_bytes,
        clock_interrupted_laps=interrupted, model_loads=5, stationary_events=sum(e['event']=='stop' for e in events),
        stationary_laps=len({e['lap_uid'] for e in events if e['event']=='stop'}),
        memory_scope='isolated process peak: corpus import, 205 source laps, five signed folds, inference caches and output rows; not model-exclusive')
    table_write(OUT/f'observations-{cadence:g}s.csv', pd.DataFrame(rows))
    dump(OUT/f'runtime-{cadence:g}s.json', runtime)
    dump(OUT/f'stop-events-{cadence:g}s.json', events)
    print(json.dumps(runtime), flush=True)


def prediction_rows(table, column, name):
    rows = table[['lap_uid', 'physical_session_id', 'fold', 'checkpoint_s', 'observed_elapsed_s', 'target_s', 'cadence_s']].copy()
    rows['prediction_s'] = table[column].to_numpy(float)
    rows['raw_final_s'] = table.raw_prediction_s.to_numpy(float)
    rows['raw_remaining_s'] = rows.raw_final_s-rows.observed_elapsed_s
    rows['model'] = name
    rows['pace_band'] = pace_band(rows.target_s, 109.734, 140.04333333333335)
    return rows


def summaries(predictions):
    overall, details, stability = [], [], []
    for (cadence, name), rows in predictions.groupby(['cadence_s', 'model']):
        for subset, table in dict(all=rows, shared_5s=rows[rows.checkpoint_s % 5 == 0],
                late_over_60s=rows[rows.checkpoint_s > 60],
                last_scheduled=rows.sort_values('checkpoint_s').groupby('lap_uid').tail(1),
                retrospective_final_10s=rows[rows.target_s-rows.observed_elapsed_s <= 10]).items():
            if len(table):
                overall.append(dict(cadence_s=cadence, model=name, subset=subset, **metrics(table),
                    physically_impossible_count=int((table.prediction_s < table.observed_elapsed_s).sum())))
        for dimension in ('checkpoint_s', 'pace_band', 'fold', 'driving_state'):
            if dimension not in rows:
                continue
            for value, table in rows.groupby(dimension):
                details.append(dict(cadence_s=cadence, model=name, dimension=dimension, value=value, **metrics(table)))
        for uid, table in rows.groupby('lap_uid'):
            table = table.sort_values('checkpoint_s')
            delta = np.diff(table.prediction_s)
            rates = delta/np.diff(table.observed_elapsed_s)
            stability.append(dict(cadence_s=cadence, model=name, lap_uid=uid,
                mean_absolute_jump_s=float(np.abs(delta).mean()), max_absolute_jump_s=float(np.abs(delta).max()),
                p95_absolute_rate_s_per_s=float(np.percentile(np.abs(rates), 95))))
    return pd.DataFrame(overall), pd.DataFrame(details), pd.DataFrame(stability)


def main(train_one_second=False):
    from scripts.prepare_barcelona_v081 import main as prepare
    prepare()
    if RESULT.exists():
        result = json.loads(RESULT.read_text(encoding='utf-8'))
        for name, digest in result['evidence_sha256'].items():
            assert file_sha(ROOT/name) == digest, name
        print('Verified frozen v081 results; no inference, fitting or rescoring repeated.', flush=True)
        return
    OUT.mkdir(parents=True, exist_ok=True)
    for cadence in (5., 1., .5):
        subprocess.run([sys.executable, '-m', 'scripts.run_barcelona_v081', '--worker', str(cadence)], cwd=ROOT, check=True)
    corpus, dev, folds = population()
    labels = dev.targets[['lap_uid', 'target_s']]
    observations = {c:pd.read_csv(OUT/f'observations-{c:g}s.csv').merge(labels, on='lap_uid', validate='many_to_one') for c in (5., 1., .5)}
    reference = observations[5.].set_index(['lap_uid', 'checkpoint_s'])
    deviation = {}
    for c in (1., .5):
        shared = observations[c].set_index(['lap_uid', 'checkpoint_s']).loc[reference.index]
        assert np.array_equal(shared.observed_elapsed_s, reference.observed_elapsed_s)
        deviation[str(c)] = {col:float(np.max(np.abs(shared[col]-reference[col]))) for col in
                            ('raw_prediction_s', 'bounded_prediction_s', 'stop_aware_prediction_s')}
        assert max(deviation[str(c)].values()) < 1e-9
    old = pd.read_csv(ROOT/'docs/DEVELOPMENT_PREDICTIONS_V080.csv').query("model=='SVR-DENSE'").set_index(['lap_uid', 'checkpoint_s'])
    old_deviation = float(np.max(np.abs(old.loc[reference.index].prediction_s-reference.raw_prediction_s)))
    assert old_deviation < 1e-9
    tables = []
    for c, table in observations.items():
        for column, name in [('raw_prediction_s', 'A-RAW'), ('bounded_prediction_s', 'A-BOUNDED'), ('stop_aware_prediction_s', 'A-STOP-AWARE')]:
            rows = prediction_rows(table, column, name)
            rows['driving_state'] = table.driving_state
            tables.append(rows)
    training = []
    training_error = None
    if train_one_second:
        one = observations[1.]
        binding = json.loads((ROOT/'docs/ML_RESULTS_V080.json').read_text(encoding='utf-8'))['compatibility']
        try:
            for f in range(5):
                train, held = one[one.fold != f], one[one.fold == f].copy()
                sparse_train = observations[5.].query('fold != @f')
                start = time.perf_counter()
                model, info = fit_one_second(train, sparse_train)
                info.update(fold=f, fit_seconds=time.perf_counter()-start, process_peak_bytes=working_memory(),
                    training_ids=sorted(train.lap_uid.unique()), held_ids=sorted(held.lap_uid.unique()),
                    training_blocks=sorted(train.physical_session_id.unique()), held_blocks=sorted(held.physical_session_id.unique()))
                assert not set(info['training_blocks']) & set(info['held_blocks'])
                held['raw_prediction_s'] = model.predict(held.loc[:, FEATURES])
                rows = prediction_rows(held, 'raw_prediction_s', 'B-1S-RAW')
                tables.append(rows)
                bounded = rows.copy()
                bounded['model'] = 'B-1S-BOUNDED'
                bounded['prediction_s'] = np.maximum(rows.prediction_s, rows.observed_elapsed_s)
                tables.append(bounded)
                old_bundle, _ = load_fold(binding, f)
                bundle = replace(old_bundle, models={'SVR-1S':model}, selected_model='SVR-1S',
                    mode='Experimental v081 1s training; development OOF only',
                    compatibility={**old_bundle.compatibility, 'v081_protocol_sha256':file_sha(ROOT/'docs/ML_PROTOCOL_V081.json')})
                LocalArtifactStore(OUT/'models').save(bundle, f'svr-1s-v081-{f}')
                training.append(info)
                dump(OUT/'training.json', training)
                print(f'Focused 1s training fold {f}: {info["fit_seconds"]:.3f}s', flush=True)
        except Exception as exc:
            training_error = f'{type(exc).__name__}: {exc}'
            print('Optional training incomplete: '+training_error, flush=True)
    predictions = pd.concat(tables, ignore_index=True)
    overall, details, stability = summaries(predictions)
    predictions.to_csv(ROOT/'docs/DEVELOPMENT_PREDICTIONS_V081.csv.gz', index=False,
                       lineterminator='\n', compression={'method':'gzip', 'mtime':0})
    table_write(ROOT/'docs/DEVELOPMENT_OVERALL_V081.csv', overall)
    table_write(ROOT/'docs/DEVELOPMENT_DETAILS_V081.csv', details)
    table_write(ROOT/'docs/DEVELOPMENT_STABILITY_V081.csv', stability)
    runtimes = [json.loads((OUT/f'runtime-{c:g}s.json').read_text()) for c in (5., 1., .5)]
    protocol = json.loads((ROOT/'docs/ML_PROTOCOL_V081.json').read_text())
    half = runtimes[-1]
    supported = bool(half['checkpoint_p95_ms'] < protocol['gates']['half_second_p95_inference_ms'] and
                     half['peak_process_working_set_bytes'] < protocol['gates']['half_second_peak_process_bytes'])
    recommendation = False
    if len(training) == 5:
        scores = overall.query("subset=='all' and cadence_s==1").set_index('model')
        gain = float(scores.loc['A-RAW', 'mae_s']-scores.loc['B-1S-RAW', 'mae_s'])
        by_fold = details.query("dimension=='fold' and cadence_s==1").pivot(index='value', columns='model', values='mae_s')
        recommendation = bool(gain >= .2 and gain/scores.loc['A-RAW', 'mae_s'] >= .02 and
                              (by_fold['B-1S-RAW'] < by_fold['A-RAW']).sum() >= 4)
    evidence_paths = [*ROOT.glob('docs/DEVELOPMENT_*V081.csv'), ROOT/'docs/DEVELOPMENT_PREDICTIONS_V081.csv.gz', ROOT/'docs/ML_PROTOCOL_V081.json',
                      *OUT.glob('*.json'), *OUT.glob('*.csv'), *OUT.glob('models/*.joblib'), *OUT.glob('models/*.json')]
    result = dict(baseline_commit='11c11f8', branch='feat/sim-telemetry-v081', development_laps=169,
        development_blocks=40, validated_laps_preserved=205, historical_test_evaluations=0,
        original_test_evaluations=1, folds_sha256=file_sha(ROOT/'docs/DEVELOPMENT_FOLDS_V080.csv'),
        compatibility=json.loads((ROOT/'docs/ML_RESULTS_V080.json').read_text())['compatibility'],
        cadence_shared_max_deviation_s=deviation, frozen_v080_max_deviation_s=old_deviation,
        runtime=runtimes, half_second_supported=supported, training=training, training_error=training_error,
        recommend_one_second_training=recommendation, operational_model='Original signed v0.7.1 SVR unchanged',
        evidence_sha256={p.relative_to(ROOT).as_posix():file_sha(p) for p in evidence_paths})
    verify_inventory(json.loads((ROOT/'docs/BASELINE_PRESERVATION_V081.json').read_text())['sha256'])
    dump(RESULT, result)
    print(overall.query("subset=='all'")[['cadence_s', 'model', 'mae_s', 'physically_impossible_count']].to_string(index=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', type=float, choices=(5., 1., .5))
    parser.add_argument('--train-one-second', action='store_true')
    args = parser.parse_args()
    worker(args.worker) if args.worker is not None else main(args.train_one_second)
