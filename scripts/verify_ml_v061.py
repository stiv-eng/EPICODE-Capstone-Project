"""Compare unchanged sklearn workflows against every frozen v0.6 prediction.

Writes only ignored validation evidence, never replaces the historical CSVs,
trains Keras, or saves model bundles. Run as python -m scripts.verify_ml_v061.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from motorsport.ingestion.acgym_importer import load_acgym_sessions
from motorsport.ingestion.gt7_importer import load_gt7_bundle
from motorsport.ml.dataset import from_sessions, independent_subset
from motorsport.ml.training import train

ROOT=Path(__file__).resolve().parents[1]


def verify():
    sessions,_=load_acgym_sessions()
    acgym=independent_subset(from_sessions(sessions,'v0.6.1 regression'))
    gt7=from_sessions([load_gt7_bundle(ROOT/'data/raw/gt7_trial_mountain_962c')],'GT7 regression')
    evidence={}
    identity=['model','partition','lap_uid','checkpoint_s']
    columns=['prediction_s','target_s','error_s','previous_lap','historical_median']
    for label,corpus,experimental in [('ACGYM',acgym,False),('GT7',gt7,True)]:
        bundle=train(corpus,experimental=experimental)
        frozen=pd.read_csv(ROOT/f'docs/{label}_ML_ERRORS_V06.csv')
        current=bundle.predictions
        joined=current.merge(frozen,on=identity,suffixes=('_current','_frozen'),validate='one_to_one')
        assert len(joined)==len(current)==len(frozen),'Frozen/current prediction population differs'
        deviations={}
        for column in columns:
            a=joined[column+'_current'].to_numpy(dtype=float)
            b=joined[column+'_frozen'].to_numpy(dtype=float)
            np.testing.assert_allclose(a,b,rtol=0,atol=1e-9,equal_nan=True,err_msg=f'{label}: {column}')
            valid=np.isfinite(a)&np.isfinite(b)
            deviations[column]=float(np.max(np.abs(a[valid]-b[valid]))) if valid.any() else None
        evidence[label]={'matched_rows':len(joined),'models':list(bundle.models),
                         'selected_model':bundle.selected_model,'max_absolute_deviation':deviations,
                         'tolerance_s':1e-9,'status':'passed'}
    artifacts=ROOT/'artifacts';artifacts.mkdir(exist_ok=True)
    (artifacts/'ML_REGRESSION_V061.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(evidence,indent=2))


if __name__=='__main__':
    verify()
