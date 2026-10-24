"""Explicit Barcelona experiment. Data-gate failure never triggers fitting."""
import json

from scripts.audit_barcelona import audit
from motorsport.ml.barcelona_experiment import run
from motorsport.ml.barcelona import ROOT,PROTOCOL,file_sha
from scripts.download_barcelona import write_json


if __name__=='__main__':
    corpus,result=audit()
    if not result['data_gate']['eligible']:
        write_json(ROOT/'docs/ML_STATUS_V07.json',dict(status='data_gate_not_met',data_gate=result['data_gate'],
            corpus_id=corpus.identity,protocol_sha256=file_sha(PROTOCOL),barcelona_models_fitted=0,
            selected_model=None,validation_metrics=None,test_metrics=None,test_evaluations=0,
            reason='Preregistered minimum not met; no fitting, forced split, learning curve or test evaluation.'))
        print('NOT FITTED: preregistered data gate failed; historical results remain unchanged.')
    else:
        bundle=run(corpus,result)
        print(json.dumps(dict(selected_model=bundle.selected_model,corpus_id=bundle.corpus_id),indent=2))
