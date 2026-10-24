"""Offline inclusive audit and reproducible Barcelona training/evaluation."""
import argparse
import json
import pandas as pd

from motorsport.ml.barcelona_recovery import load_corpus, data_gate, ROOT
from motorsport.ml.barcelona_experiment import dump, table_write


def audit():
    corpus, result = load_corpus()
    result['technical_eligibility'] = data_gate(corpus, result)
    dump(ROOT/'docs/BARCELONA_AUDIT_V071.json', result)
    for name, key in [('RECORDINGS', 'records'), ('LAPS', 'lap_audit')]:
        table_write(ROOT/f'docs/BARCELONA_{name}_V071.csv', pd.DataFrame(result[key]))
    print(json.dumps({k:v for k,v in result.items() if k not in ('records', 'lap_audit')}, indent=2), flush=True)
    return corpus, result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit-only', action='store_true')
    args = parser.parse_args()
    corpus, result = audit()
    if not args.audit_only:
        from motorsport.ml.barcelona_experiment_v071 import run
        bundle = run(corpus, result)
        print('Selected on validation:', bundle.selected_model, flush=True)
