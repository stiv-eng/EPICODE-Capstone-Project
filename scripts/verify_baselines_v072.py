"""Frozen classical regressions; Barcelona test is compared as stored evidence only."""
import json
import numpy as np
import pandas as pd

from motorsport.ml.barcelona_recovery import ROOT,load_corpus,predict
from motorsport.ml.barcelona_experiment_v071 import load_bundle
from motorsport.ml.diagnosis_v072 import verify_inventory
from motorsport.ml.barcelona_experiment import dump
from scripts.verify_ml_v061 import verify


def main():
    preserved=json.loads((ROOT/'docs/BASELINE_PRESERVATION_V072.json').read_text(encoding='utf-8'))['sha256']
    verify_inventory(preserved)
    verify()
    historical=json.loads((ROOT/'artifacts/ML_REGRESSION_V061.json').read_text(encoding='utf-8'))
    corpus,_=load_corpus();bundle=load_bundle(corpus)
    frozen=pd.read_csv(ROOT/'docs/BARCELONA_PREDICTIONS_V071.csv')
    keys=['lap_uid','checkpoint_s','model','partition']
    joined=bundle.predictions.merge(frozen,on=keys,suffixes=('_local','_frozen'),validate='one_to_one')
    assert len(joined)==len(frozen)==1170
    for name in ('prediction_s','target_s','error_s','previous_lap','historical_median'):
        np.testing.assert_allclose(joined[name+'_local'],joined[name+'_frozen'],atol=1e-9,rtol=0,equal_nan=True)
    sources={l.lap_uid:l for l in corpus.laps}
    rows=frozen.query("model=='SVR' and partition=='validation'")
    deviation=[];baseline=[]
    for row in rows.itertuples(index=False):
        result=predict(sources[row.lap_uid],row.checkpoint_s,bundle.models['SVR'],bundle.feature_names,
                       bundle.history,model_domain=bundle.domain,date_reliability=bundle.date_reliability)
        deviation.append(abs(result.predicted_final_s-row.prediction_s))
        baseline.append(abs(result.baseline_s-row.historical_median))
    assert max(deviation)<1e-9 and max(baseline)<1e-9
    verify_inventory(preserved)
    result=dict(status='passed',historical=historical,barcelona=dict(stored_frozen_rows=1170,
        reference_validation_predictions_verified=len(rows),max_prediction_deviation_s=max(deviation),
        max_median_deviation_s=max(baseline),new_historical_test_predictions=0,
        original_test_evaluations=1,reference_artifacts_unchanged=True))
    dump(ROOT/'docs/FROZEN_REGRESSION_V072.json',result)
    print(json.dumps(result['barcelona'],indent=2))


if __name__=='__main__':main()
