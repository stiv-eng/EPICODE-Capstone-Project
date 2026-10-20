import numpy as np
import pandas as pd
from motorsport_ui.analytics import (clean_lap_table, driver_summary, stint_summary,
                                    degradation_regression, telemetry_delta)


def example_laps():
    return pd.DataFrame({
        'LapTime': pd.to_timedelta([101,102,103,104,105,99], unit='s'),
        'Driver': ['AAA']*5+['BBB'], 'LapNumber': [1,2,3,4,5,1],
        'Stint': [1,1,1,1,1,1], 'TyreLife': [1,2,3,4,5,1],
        'Compound': ['MEDIUM']*6, 'IsAccurate': [True]*6,
        'Deleted': [False]*6,
    })


def test_summary_and_stint():
    df = clean_lap_table(example_laps())
    assert len(df) == 6
    assert driver_summary(df).iloc[0]['Driver'] == 'BBB'
    assert len(stint_summary(df)) == 2
    assert df.loc[df['Driver']=='AAA','LapTimeSeconds'].min() == 101


def test_linear_degradation_known_slope():
    result = degradation_regression(clean_lap_table(example_laps()))
    assert len(result) == 1
    assert abs(result.iloc[0]['slope_s_per_tyre_lap'] - 1.0) < 1e-8
    assert result.iloc[0]['r2'] > .999


def test_delta_telemetry_sign_and_limit():
    reference = pd.DataFrame({'Distance': [0,50,100], 'elapsed_s':[0,1,2]})
    other = pd.DataFrame({'Distance': [0,50,100], 'elapsed_s':[0,1.2,2.4]})
    delta = telemetry_delta(reference, other)
    assert np.isclose(delta.iloc[-1]['delta_s'], 0.4)
    assert np.isclose(delta.iloc[0]['delta_s'], 0)
