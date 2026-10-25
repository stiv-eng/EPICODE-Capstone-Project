"""Composable file -> audit -> canonical telemetry -> validated laps pipeline."""
from dataclasses import dataclass
from pathlib import Path
import hashlib

import pandas as pd
import numpy as np

from .ingestion.csv_importer import read_csv
from .ingestion.parquet_importer import read_parquet
from .processing.schema import CANONICAL
from .processing.normalization import normalize
from .processing.validation import quality_report
from .processing.laps import detect_laps, LapResult
from .analytics.session_metrics import session_metrics


@dataclass
class TelemetrySession:
    raw: pd.DataFrame
    data: pd.DataFrame
    metadata: dict
    raw_quality: dict
    quality: dict
    laps: LapResult
    metrics: dict


def load_session(source, filename=None, profile=CANONICAL, csv_sep=None):
    name = filename or str(source)
    suffix = Path(name).suffix.lower()
    if suffix == '.parquet':
        raw, metadata = read_parquet(source)
    elif suffix == '.csv':
        raw, metadata = read_csv(source, sep=csv_sep)
    else:
        raise ValueError('Supported telemetry formats: .parquet and .csv')
    metadata['filename'] = Path(name).name
    return build_session(raw, metadata, profile)


def build_session(raw, metadata, profile=CANONICAL, validated_laps=None, lap_elapsed=None):
    """Compose standard readers or a source-specific, independently checked adapter."""
    data, normalization = normalize(raw, profile)
    metadata = {**metadata, 'normalization': normalization}
    if 'session_id' not in metadata:
        fingerprint = pd.util.hash_pandas_object(raw, index=True).to_numpy().tobytes()
        schema = repr([(str(c),str(raw[c].dtype)) for c in raw]).encode()
        metadata['session_id'] = 'local:'+hashlib.sha256(schema+fingerprint).hexdigest()
    # Source time is audited only after its units are explicitly declared.
    time_source = normalization['mappings'].get('elapsed_s', {}).get('source')
    raw_quality = quality_report(raw)
    metadata['source_time_column'] = time_source
    laps = validated_laps if validated_laps is not None else detect_laps(data)
    # Unvalidated source labels remain in raw; only validated complete laps
    # become canonical labels for verified-lap analysis and comparison.
    for column in ['lap_id', 'lap_elapsed_s']:
        if column in data:
            del data[column]
    if {'lap_id', 'lap_elapsed_s'} & set(raw.columns):
        metadata['normalization']['notes'].append(
            'Source lap labels are retained in raw; canonical lap labels require validated complete boundaries.')
    if laps.available:
        lap_ids = pd.array([pd.NA] * len(data), dtype='Int64')
        lap_times = np.full(len(data), np.nan)
        for lap in laps.laps.itertuples(index=False):
            rows = slice(lap.start_sample, lap.end_sample)
            lap_ids[rows] = lap.lap_id
            lap_times[rows] = (np.asarray(lap_elapsed)[rows] if lap_elapsed is not None
                               else data['elapsed_s'].iloc[rows].to_numpy() - lap.start_s)
        data['lap_id'], data['lap_elapsed_s'] = lap_ids, lap_times
    quality = quality_report(data, 'elapsed_s')
    return TelemetrySession(raw, data, metadata, raw_quality, quality, laps, session_metrics(data))
