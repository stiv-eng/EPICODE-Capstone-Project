"""Freeze v080 evidence and preregister the single focused v081 comparison."""
import json
import subprocess

from motorsport.ml.barcelona_recovery import ROOT, RAW, file_sha
from motorsport.ml.barcelona_experiment import dump
from motorsport.ml.diagnosis_v072 import verify_inventory


def main():
    path = ROOT/'docs/BASELINE_PRESERVATION_V081.json'
    if not path.exists():
        previous = ROOT/'docs/NEXT_RELEASE_RECOMMENDATION.md'
        archive = ROOT/'docs/NEXT_RELEASE_RECOMMENDATION_V080.md'
        if not archive.exists():
            archive.write_bytes(previous.read_bytes())
        tracked = subprocess.check_output(['git', 'ls-files', 'docs'], cwd=ROOT, text=True).splitlines()
        paths = [ROOT/p for p in tracked if p != 'docs/NEXT_RELEASE_RECOMMENDATION.md']
        paths += [archive, *ROOT.glob('artifacts/barcelona_v*/models/*'), *ROOT.glob('artifacts/models/*'),
                  *ROOT.glob('.vscode/*'), *RAW.rglob('*.ld'), *RAW.rglob('*.ldx')]
        # Ignore signing keys in the public inventory; authentic loaders verify them.
        paths = [p for p in paths if p.is_file() and not p.name.startswith('.')]
        dump(path, dict(baseline_commit='11c11f8', baseline_branch='feat/sim-telemetry-v080',
            initial_tree='clean', prior_recommendation_sha256=file_sha(archive),
            sha256={p.relative_to(ROOT).as_posix():file_sha(p) for p in paths}))
    verify_inventory(json.loads(path.read_text(encoding='utf-8'))['sha256'])
    protocol = ROOT/'docs/ML_PROTOCOL_V081.json'
    if not protocol.exists():
        dump(protocol, dict(version='high-frequency-stop-aware-v081-1', baseline_commit='11c11f8',
            population='All original 169 development laps / 40 blocks, original five v072 folds; 36 historical test laps excluded before representation',
            model_A='Existing signed v080 SVR-DENSE trained at 5 s; no refit',
            model_B='One 1 s-trained direct RBF SVR, C10 epsilon0.5 gamma scale, same 13 features, five outer folds; no tuning',
            penalty='B: weight per lap = number of A training snapshots / number of training laps. Each 1 s row gets that mass divided by its lap snapshot count. Sum(C*weights) matches A, and each lap mass matches A. Imputer/scaler fit only outer training; distribution change disclosed.',
            inference='5 / 1 / 0.5 elapsed seconds; last source sample at or before nominal, freshness<=100ms, stop on reset/missing clock/gap>200ms; no future interpolation',
            detector=dict(stop_speed_kmh=2., stop_persistence_s=1., resume_speed_kmh=4., resume_persistence_s=.3,
                          max_source_gap_s=.2, resume_blend_s=2.),
            correction='Separate raw, max(raw,observed), and stationary elapsed+causal remaining at observed low-speed onset. Confirm from source samples only, not replay wall time; 2 s positive resume-offset decay.',
            gates=dict(half_second_p95_inference_ms=100., half_second_peak_process_bytes=1500000000,
                       B_minimum_MAE_gain_s=.2, B_minimum_relative_gain=.02, B_minimum_improved_folds=4),
            reporting='Equal-lap metrics; shared cutoffs before cadence claims; per checkpoint survivors, pace, late tails, stability, raw impossibility, real stop counts, synthetic separate',
            promotion='No automatic operational promotion; all results reused development OOF, no fresh final test'))
    print('Preservation inventory verified; v081 protocol frozen before evaluation.', flush=True)


if __name__ == '__main__':
    main()
