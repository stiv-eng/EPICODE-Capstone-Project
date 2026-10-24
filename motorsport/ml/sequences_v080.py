"""Target-free ordered observations and training-only sequence transforms.

Keras/Torch are lazy imports. The default offline reference never loads them.
"""
from dataclasses import dataclass
import os

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

from .dataset import CORE
from .features import causal_prefix

CHANNELS = ('speed_kmh', 'throttle_pct', 'brake_pct', 'rpm', 'gear', 'steering')
CHUNK_S = 2.
MAX_STEPS = 301  # Fixed 600s support, including a terminal partial chunk.


def sequence(source, checkpoint):
    frame, quality = causal_prefix(source, checkpoint)
    t = frame.lap_elapsed_s.to_numpy(float)
    observed = float(t[-1])
    if observed > 600.:
        raise ValueError('Sequence support is at most 600 observed seconds')
    values = frame.reindex(columns=CHANNELS).to_numpy(float).copy()
    for j, name in enumerate(CHANNELS):
        if name in CORE:
            lo, hi = CORE[name]
            values[(values[:, j] < lo) | (values[:, j] > hi), j] = np.nan
    if source.steering_unit != 'deg':
        values[:, -1] = np.nan
    # Every grid value looks backward only. Include actual terminal observation
    # so late partial chunks have the same horizon as the aggregate features.
    grid = np.arange(0, int(np.floor(observed*10+1e-9))+1, dtype=float)/10
    grid = grid[grid <= observed]
    if not len(grid) or observed-grid[-1] > 1e-9:
        grid = np.r_[grid, observed]
    index = np.searchsorted(t, grid, side='right')-1
    available = (index >= 0) & ((grid-t[np.maximum(index, 0)]) <= .2+1e-9)
    sampled = values[np.maximum(index, 0)].copy()
    sampled[~available] = np.nan
    chunks = []
    # Right-endpoint boundary belongs to preceding chunk: no extra empty step.
    bins = np.maximum(0, np.ceil(grid/CHUNK_S-1e-9).astype(int)-1)
    for group in range(int(bins.max())+1):
        part = sampled[bins == group]
        finite = np.isfinite(part)
        count = finite.sum(axis=0)
        means = np.divide(np.where(finite, part, 0.).sum(axis=0), count,
                          out=np.full(6, np.nan), where=count > 0)
        fractions = count/max(1, len(part))
        duration = min(CHUNK_S, max(0., observed-group*CHUNK_S))/CHUNK_S
        chunks.append(np.r_[means, fractions, duration])
    return np.asarray(chunks, dtype=np.float32), quality


@dataclass
class SequenceTransform:
    median: np.ndarray
    mean: np.ndarray
    scale: np.ndarray
    context_imputer: object
    context_scaler: object

    @classmethod
    def fit(cls, sequences, context, unique_indices=None):
        # Caller provides longest prefix of each FIT lap once; no padding or
        # held-out values affect these statistics.
        unique_indices = range(len(sequences)) if unique_indices is None else unique_indices
        values = np.concatenate([sequences[i][:, :6] for i in unique_indices])
        median = np.array([np.median(c[np.isfinite(c)]) if np.isfinite(c).any() else 0. for c in values.T])
        filled = np.where(np.isfinite(values), values, median)
        mean = filled.mean(axis=0)
        scale = filled.std(axis=0)
        scale[scale < 1e-6] = 1.
        imputer = SimpleImputer(strategy='median', keep_empty_features=True).fit(context)
        scaler = StandardScaler().fit(imputer.transform(context))
        return cls(median, mean, scale, imputer, scaler)

    def transform(self, sequences, context, pad_to=None):
        size = max(len(s) for s in sequences) if pad_to is None else pad_to
        if size > MAX_STEPS or any(len(s) > size for s in sequences):
            raise ValueError('Sequence exceeds padding support')
        x = np.zeros((len(sequences), size, 13), np.float32)
        mask = np.zeros((len(sequences), size), bool)
        for i, s in enumerate(sequences):
            a = s.copy()
            a[:, :6] = (np.where(np.isfinite(a[:, :6]), a[:, :6], self.median)-self.mean)/self.scale
            x[i, :len(a)] = a
            mask[i, :len(a)] = True
        c = self.context_scaler.transform(self.context_imputer.transform(context)).astype(np.float32)
        return dict(telemetry=x, observed_mask=mask, context=c)

    def flat(self, sequences, context):
        data = self.transform(sequences, context, MAX_STEPS)
        return np.concatenate([data['telemetry'].reshape(len(sequences), -1),
                               data['observed_mask'].astype(np.float32), data['context']], axis=1)


def keras_api():
    os.environ.setdefault('KERAS_BACKEND', 'torch')
    os.environ.setdefault('CUDA_VISIBLE_DEVICES', '-1')
    import keras
    if keras.backend.backend() == 'torch':
        import torch
        torch.set_num_threads(2)
        torch.use_deterministic_algorithms(True)
    return keras


def make_gru(seed=42):
    keras = keras_api()
    keras.utils.set_random_seed(seed)
    x = keras.Input((None, 13), name='telemetry')
    mask = keras.Input((None,), dtype='bool', name='observed_mask')
    context = keras.Input((13,), name='context')
    state = keras.layers.GRU(16, kernel_regularizer=keras.regularizers.l2(.001), name='ordered_gru')(x, mask=mask)
    joint = keras.layers.Concatenate()([state, context])
    head = keras.layers.Dense(8, activation='relu')(joint)
    y = keras.layers.Dense(1, name='standardized_remaining')(head)
    net = keras.Model(dict(telemetry=x, observed_mask=mask, context=context), y)
    net.compile(optimizer=keras.optimizers.Adam(.003, clipnorm=1.), loss='mse')
    return net


def raw_gru(net, data, mean, scale):
    return np.asarray(net.predict(data, batch_size=128, verbose=0)).reshape(-1)*scale+mean
