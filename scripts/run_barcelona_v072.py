"""Explicit offline diagnostic/feature experiment; no new historical-test scoring."""
import argparse
import json
import pandas as pd

from motorsport.ml.barcelona_recovery import ROOT,load_corpus
from motorsport.ml.barcelona_experiment_v071 import load_bundle
from motorsport.ml.diagnosis_v072 import audit,audit_source_progress,new_feature_information,preserved_inventory,verify_inventory
from motorsport.ml.barcelona_experiment import dump


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit-only',action='store_true')
    args=parser.parse_args()
    preserved=preserved_inventory()
    corpus,_=load_corpus();reference=load_bundle(corpus)
    development,_,_=audit(corpus,reference)
    audit_source_progress(development)
    if not args.audit_only:
        from motorsport.ml.development_v072 import run
        bundle=run(corpus)
        new_feature_information(pd.read_csv(ROOT/'docs/DEVELOPMENT_FEATURES_V072.csv'))
        print(json.dumps(dict(selected_development_variant=bundle.selected_model,
                             production_reference='unchanged v071 SVR',historical_test_evaluations=0),indent=2),flush=True)
    verify_inventory(preserved)
    dump(ROOT/'docs/BASELINE_PRESERVATION_V072.json',dict(status='passed',sha256=preserved,
        original_reference_untouched=True,historical_test_experimental_evaluations=0))


if __name__=='__main__':main()
