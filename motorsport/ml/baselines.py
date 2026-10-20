"""Past-only references. Held-out lap labels must never enter history."""
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class CompletedLap:
    lap_uid: str
    domain: tuple
    end_order: tuple
    target_s: float


def reference_history(corpus, allowed_ids):
    targets = corpus.targets.set_index('lap_uid')
    result = []
    for lap in corpus.laps:
        if lap.lap_uid in allowed_ids:
            # Same-session lap ends precede next starts. This is metadata only;
            # a verified target is never copied into the current replay source.
            end = (*lap.start_order[:2],lap.start_order[2]+float(targets.loc[lap.lap_uid,'target_s']))
            result.append(CompletedLap(lap.lap_uid,lap.domain,end,float(targets.loc[lap.lap_uid,'target_s'])))
    return result


def baseline_predictions(source, history=()):
    previous = sorted([lap for lap in history if lap.lap_uid!=source.lap_uid and
        lap.domain==source.domain and lap.end_order<=source.start_order and
        np.isfinite(lap.target_s) and lap.target_s>0],key=lambda lap:lap.end_order)
    if not previous:
        return {'previous_lap':None,'historical_median':None,'history_laps':0,
                'status':'unavailable: no earlier completed comparable allowed lap'}
    return {'previous_lap':previous[-1].target_s,
        'historical_median':float(np.median([lap.target_s for lap in previous])),
        'history_laps':len(previous),'status':'past-only reference'}
