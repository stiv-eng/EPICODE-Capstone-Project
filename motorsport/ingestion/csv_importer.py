"""CSV reader with explicit delimiter support and conservative inference."""
from io import BytesIO
import csv

import pandas as pd


def read_csv(source, sep=None):
    if isinstance(source, bytes):
        source = BytesIO(source)
    if sep is None:
        if hasattr(source, 'read'):
            offset = source.tell()
            sample = source.read(8192)
            source.seek(offset)
        else:
            with open(source, 'rb') as stream:
                sample = stream.read(8192)
        if isinstance(sample, bytes):
            sample = sample.decode('utf-8-sig', errors='replace')
        try:
            sep = csv.Sniffer().sniff(sample, delimiters=',;\t|').delimiter
        except csv.Error:
            sep = ','  # Includes legitimate single-channel CSV files.
    frame = pd.read_csv(source, sep=sep, engine='python' if len(sep) > 1 else 'c')
    return frame, {'format': 'CSV', 'rows': len(frame), 'columns': len(frame.columns)}
