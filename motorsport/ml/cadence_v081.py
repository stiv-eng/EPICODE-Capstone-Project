"""One controlled denser-training candidate; never called by the application."""
import numpy as np

from .features import FEATURES
from .training import make_models


def matched_penalty_weights(train, reference):
    if set(train.lap_uid) != set(reference.lap_uid):
        raise ValueError('Training populations differ')
    # A's mean-one inverse-count weights give every lap N_A / L_A mass.
    # Keep this exact total in B; do NOT renormalize B weights to mean one.
    mass = len(reference)/reference.lap_uid.nunique()
    return mass/train.groupby('lap_uid').lap_uid.transform('size').to_numpy(float)


def fit_one_second(train, reference):
    weights = matched_penalty_weights(train, reference)
    model = make_models()['SVR']
    model.fit(train.loc[:, FEATURES], train.target_s, model__sample_weight=weights)
    return model, dict(reference_snapshots=len(reference), candidate_snapshots=len(train),
        unique_training_laps=train.lap_uid.nunique(), reference_total_weight=float(len(reference)),
        candidate_total_weight=float(weights.sum()), per_lap_weight=float(len(reference)/train.lap_uid.nunique()),
        mean_candidate_weight=float(weights.mean()), C=10., epsilon=.5,
        total_penalty_mass=float(10.*weights.sum()), preprocessing='outer-training-only imputer and scaler, unweighted')
