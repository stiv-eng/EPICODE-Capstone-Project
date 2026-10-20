"""Read Parquet bytes, paths or binary streams without changing the source."""
from io import BytesIO

import pandas as pd
import pyarrow.parquet as pq


def read_parquet(source):
    if isinstance(source, bytes):
        source = BytesIO(source)
    parquet = pq.ParquetFile(source)
    frame = parquet.read().to_pandas()
    if not frame.columns.is_unique:
        raise ValueError('Duplicate column names are not supported.')
    metadata = {
        'format': 'Parquet', 'rows': parquet.metadata.num_rows,
        'columns': parquet.metadata.num_columns,
        'row_groups': parquet.num_row_groups,
        'arrow_schema': str(parquet.schema_arrow),
        'source_metadata': {
            k.decode('utf-8', errors='replace'): v.decode('utf-8', errors='replace')
            for k, v in (parquet.schema_arrow.metadata or {}).items()
        },
    }
    return frame, metadata
