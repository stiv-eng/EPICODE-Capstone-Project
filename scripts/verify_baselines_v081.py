"""Verify original files and numerical references without rewriting old reports."""
import json

import numpy as np
import pandas as pd

from motorsport.ml.barcelona_recovery import ROOT, load_corpus, predict
from motorsport.ml.barcelona_experiment_v071 import load_bundle
from motorsport.ml.barcelona_experiment import dump
from motorsport.ml.diagnosis_v072 import verify_inventory
from scripts.verify_ml_v061 import verify


def main():
    inventory = json.loads((ROOT/'docs/BASELINE_PRESERVATION_V081.json').read_text(encoding='utf-8'))
    verify_inventory(inventory['sha256'])
    verify()
    corpus, _ = load_corpus()
    assert len(corpus.laps) == len(corpus.targets) == 205
    bundle = load_bundle(corpus)
    frozen = pd.read_csv(ROOT/'docs/BARCELONA_PREDICTIONS_V071.csv')
    keys = ['lap_uid', 'checkpoint_s', 'model', 'partition']
    joined = bundle.predictions.merge(frozen, on=keys, suffixes=('_local', '_frozen'), validate='one_to_one')
    assert len(joined) == len(frozen) == 1170
    for name in ('prediction_s', 'target_s', 'error_s', 'previous_lap', 'historical_median'):
        np.testing.assert_allclose(joined[name+'_local'], joined[name+'_frozen'], atol=1e-9, rtol=0, equal_nan=True)
    sources = {lap.lap_uid:lap for lap in corpus.laps}
    errors = []
    for row in frozen.query("model=='SVR' and partition=='validation'").itertuples(index=False):
        value = predict(sources[row.lap_uid], row.checkpoint_s, bundle.models['SVR'], bundle.feature_names,
                        bundle.history, model_domain=bundle.domain, date_reliability=bundle.date_reliability)
        errors.append(abs(value.predicted_final_s-row.prediction_s))
    assert max(errors) < 1e-9
    verify_inventory(inventory['sha256'])
    dump(ROOT/'docs/FROZEN_REGRESSION_V081.json', dict(status='passed', preserved_files=len(inventory['sha256']),
        validated_laps=205, stored_barcelona_rows=1170, current_validation_predictions=len(errors),
        maximum_deviation_s=max(errors), historical_test_predictions_generated=0,
        monza_gt7=json.loads((ROOT/'artifacts/ML_REGRESSION_V061.json').read_text())))
    print('v081 preservation and frozen numerical regressions passed.', flush=True)


if __name__ == '__main__':
    main()
