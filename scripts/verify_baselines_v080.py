"""Verify preserved files, signed models and original regression evidence."""
import json

import numpy as np
import pandas as pd

from motorsport.ml.barcelona_recovery import ROOT, load_corpus, predict
from motorsport.ml.barcelona_experiment_v071 import load_bundle
from motorsport.ml.diagnosis_v072 import verify_inventory
from motorsport.ml.barcelona_experiment import dump
from scripts.verify_ml_v061 import verify


def main():
    preserved = json.loads((ROOT/'docs/BASELINE_PRESERVATION_V080.json').read_text(encoding='utf-8'))['sha256']
    verify_inventory(preserved)
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
    rows = frozen.query("model=='SVR' and partition=='validation'")
    deviations = []
    for row in rows.itertuples(index=False):
        value = predict(sources[row.lap_uid], row.checkpoint_s, bundle.models['SVR'], bundle.feature_names,
                        bundle.history, model_domain=bundle.domain, date_reliability=bundle.date_reliability)
        deviations.append(abs(value.predicted_final_s-row.prediction_s))
    assert max(deviations) < 1e-9
    verify_inventory(preserved)
    result = dict(status='passed', files_preserved=len(preserved), all_validated_laps=205,
        monza_gt7=json.loads((ROOT/'artifacts/ML_REGRESSION_V061.json').read_text(encoding='utf-8')),
        barcelona_stored_frozen_rows=1170, barcelona_validation_predictions=330,
        barcelona_max_prediction_deviation_s=max(deviations), new_historical_test_predictions=0,
        original_test_evaluations=1, v071_v072_models_results_and_f5_unchanged=True)
    dump(ROOT/'docs/FROZEN_REGRESSION_V080.json', result)
    print(json.dumps({k:v for k, v in result.items() if k != 'monza_gt7'}, indent=2))


if __name__ == '__main__':
    main()
