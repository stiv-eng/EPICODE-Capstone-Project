"""Explicit offline dense SVR, ordered Ridge and Keras GRU experiment."""
import json
import os
import argparse

from motorsport.ml.barcelona_recovery import ROOT, load_corpus
from motorsport.ml.diagnosis_v072 import verify_inventory
from motorsport.ml.dense_experiment_v080 import run, rebuild_artifacts

os.environ.setdefault('MPLCONFIGDIR', str(ROOT/'artifacts/matplotlib'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rebuild-artifacts', action='store_true',
                        help='Restore missing fold/research artifacts from development only; no outer scoring')
    options = parser.parse_args()
    preservation = json.loads((ROOT/'docs/BASELINE_PRESERVATION_V080.json').read_text(encoding='utf-8'))['sha256']
    verify_inventory(preservation)
    corpus, _ = load_corpus()
    assert len(corpus.laps) == 205
    result = run(corpus)
    if options.rebuild_artifacts:
        rebuild_artifacts(corpus)
    verify_inventory(preservation)
    print(json.dumps({k:result[k] for k in ('development_laps', 'checkpoints', 'historical_test_evaluations',
                                          'sparse_reference_max_deviation_s', 'operational_reference')}, indent=2))


if __name__ == '__main__':
    main()
