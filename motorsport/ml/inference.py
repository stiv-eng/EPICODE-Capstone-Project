"""Model-agnostic retrospective replay. This API has no final-target argument."""
from dataclasses import dataclass
import pandas as pd

from .features import prefix_features
from .baselines import baseline_predictions


@dataclass(frozen=True)
class Prediction:
    checkpoint_s: float
    predicted_final_s: float | None
    baseline_s: float | None
    observed_elapsed_s: float
    quality: dict
    mode: str


def predict(source,checkpoint,model=None,feature_names=(),history=(),baseline='historical_median',model_domain=None):
    features,quality = prefix_features(source,checkpoint)
    if baseline not in ('previous_lap','historical_median'):
        raise ValueError('Unknown baseline')
    reference = baseline_predictions(source,history)[baseline]
    if model is None:
        value,mode = reference,'Baseline-only retrospective replay'
    else:
        if model_domain is None or tuple(model_domain)!=source.domain:
            raise ValueError('Model car/track domain does not match replay source')
        if not feature_names or set(feature_names)-set(features):
            raise ValueError('Model expects unavailable/noncausal features')
        row = pd.DataFrame([{name:features[name] for name in feature_names}])
        value,mode = float(model.predict(row)[0]),'ML retrospective replay'
    return Prediction(float(checkpoint),value,reference,quality['observed_elapsed_s'],quality,mode)


def retrospective_error(prediction,verified_target_s):
    """Explicit evaluation layer, called only after predictive computation."""
    return None if prediction.predicted_final_s is None else prediction.predicted_final_s-verified_target_s
