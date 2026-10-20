"""Finite source-coordinate views, with explicit validity and no finish inference."""
import numpy as np

from .timebase import numeric
from .session_metrics import chart_sample


def position_view(frame,color_channel='speed_kmh',max_points=5000):
    xy=np.c_[numeric(frame,'pos_x'),numeric(frame,'pos_y')]
    finite=np.isfinite(xy).all(axis=1)
    stats={'samples':len(frame),'finite_positions':int(finite.sum()),
           'invalid_positions':int((~finite).sum()),'varying':False}
    if finite.sum()<3 or not np.any(np.ptp(xy[finite],axis=0)>0):
        return frame.iloc[:0],stats
    stats['varying']=True
    available=frame.loc[finite]
    return chart_sample(available,['pos_x','pos_y',color_channel],max_points=max_points),stats
