from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from test_progression_v080 import source
from motorsport.ml.features import prefix_features, FEATURES
from motorsport.ml.sequences_v080 import sequence, SequenceTransform, make_gru, raw_gru, keras_api


def test_order_and_full_prefix_past_sixty_seconds(source):
    seq, quality = sequence(source, 75.)
    assert len(seq) == 38 and quality['observed_elapsed_s'] == 75.
    assert seq[-1, -1] == .5
    first, _ = sequence(source, 5.)
    np.testing.assert_array_equal(first[:2], seq[:2])
    assert seq[0, 3] < seq[-1, 3]


def test_sequence_future_invariance_and_source_timestamp_support(source):
    seq, q = sequence(source, 20.013)
    changed = source.frame.copy()
    changed.loc[changed.lap_elapsed_s > q['observed_elapsed_s'], ['speed_kmh', 'throttle_pct', 'rpm']] = 999999.
    np.testing.assert_array_equal(sequence(replace(source, frame=changed), 20.013)[0], seq)
    assert q['observed_elapsed_s'] == 20.


def test_missing_optional_channels_and_declared_steering_units(source):
    seq, _ = sequence(replace(source, steering_unit='unknown', frame=source.frame.drop(columns='gear')), 10.)
    assert np.isnan(seq[:, 4:6]).all()
    assert (seq[:, 10:12] == 0).all()
    with pytest.raises(ValueError, match='gap'):
        sequence(replace(source, frame=source.frame.drop(index=range(20, 50))), 10.)


def test_training_only_normalization_and_explicit_padding_mask(source):
    a, _ = sequence(source, 5.)
    b, _ = sequence(source, 20.)
    context = pd.DataFrame([prefix_features(source, 5.)[0], prefix_features(source, 20.)[0]], columns=FEATURES)
    prep = SequenceTransform.fit([a], context.iloc[:1])
    original = prep.mean.copy()
    extreme = b.copy(); extreme[:, :6] += 10000
    data = prep.transform([a, extreme], context)
    np.testing.assert_array_equal(original, prep.mean)
    assert data['observed_mask'][0].sum() == len(a)
    assert not data['observed_mask'][0, len(a):].any()
    assert (data['telemetry'][0, len(a):] == 0).all()
    assert data['observed_mask'][1].all()
    assert data['telemetry'].shape == (2, len(b), 13)


def test_actual_keras_gru_shape_mask_determinism_and_roundtrip(source, tmp_path):
    pytest.importorskip('torch')
    a, _ = sequence(source, 5.)
    context = pd.DataFrame([prefix_features(source, 5.)[0]], columns=FEATURES)
    prep = SequenceTransform.fit([a], context)
    small = prep.transform([a], context)
    large = prep.transform([a], context, pad_to=len(a)+5)
    model = make_gru(42)
    assert model.count_params() < 3000
    p = raw_gru(model, small, 80., 20.)
    assert p.shape == (1,)
    np.testing.assert_array_equal(raw_gru(model, small, 80., 20.), p)
    np.testing.assert_allclose(raw_gru(model, large, 80., 20.), p, atol=1e-5)
    model.fit(small, np.array([0.]), epochs=1, verbose=0)
    model.save(tmp_path/'pilot.keras')
    loaded = keras_api().models.load_model(tmp_path/'pilot.keras', safe_mode=True, compile=False)
    np.testing.assert_allclose(raw_gru(model, small, 80., 20.), raw_gru(loaded, small, 80., 20.), atol=1e-7)
