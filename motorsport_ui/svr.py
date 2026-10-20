"""Porting del modello SVR da Codes/Page_3.py del repository di origine.

La funzione originale comprendeva train/test e plot nello stesso blocco:
qui il preprocessing ML resta puro, mentre Streamlit controlla la pagina.
"""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVR

FEATURES = ['Compound', 'SessionType', 'LapNumber', 'AvgSpeed', 'ThrottleMean', 'BrakeTime']


def lap_features(session, session_code, driver):
    """Un record per giro cronometrato, usando le feature finali del giro."""
    laps = session.laps.pick_drivers(driver)
    laps = laps.loc[laps['LapTime'].notna()].copy()
    for col in ['PitInTime', 'PitOutTime']:
        if col in laps:
            laps = laps.loc[laps[col].isna()]
    if 'IsAccurate' in laps:
        laps = laps.loc[laps['IsAccurate'].fillna(False).astype(bool)]
    rows = []
    for _, lap in laps.iterrows():
        try:
            tel = lap.get_car_data()
            if tel is None or len(tel) < 2:
                continue
            time_s = pd.to_timedelta(tel['Time']).dt.total_seconds().to_numpy()
            dt = np.diff(time_s)
            brake = tel['Brake'].astype(bool).to_numpy()
            brake_time = float(np.sum(np.maximum(dt, 0) * brake[1:]))
            rows.append({'SessionType': session_code, 'Compound': str(lap['Compound']),
                         'LapNumber': int(lap['LapNumber']),
                         'AvgSpeed': float(tel['Speed'].mean()),
                         'ThrottleMean': float(tel['Throttle'].mean()),
                         'BrakeTime': brake_time,
                         'LapTime': lap['LapTime'].total_seconds()})
        except (KeyError, TypeError, ValueError, IndexError):
            continue
    return pd.DataFrame(rows, columns=FEATURES + ['LapTime'])


def fit_svr(frame, seed=42):
    """Split prima del preprocessing: scaler/encoder sono stimati solo sul train."""
    if len(frame) < 8:
        raise ValueError('Sono necessari almeno otto giri validi per addestrare SVR.')
    x_train, x_test, y_train, y_test = train_test_split(
        frame[FEATURES], frame['LapTime'], test_size=.25, random_state=seed)
    preprocessor = ColumnTransformer([
        ('numerical', Pipeline([('imputer', SimpleImputer(strategy='median')),
                                ('scaler', StandardScaler())]),
         ['LapNumber', 'AvgSpeed', 'ThrottleMean', 'BrakeTime']),
        ('categorical', Pipeline([('imputer', SimpleImputer(strategy='most_frequent')),
                                  ('encoder', OneHotEncoder(handle_unknown='ignore'))]),
         ['Compound', 'SessionType']),
    ])
    model = Pipeline([('preprocessor', preprocessor),
                      ('regressor', SVR(kernel='rbf', C=10., epsilon=.05, gamma='scale'))])
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    scores = {'MAE_s': float(mean_absolute_error(y_test, predictions)),
              'RMSE_s': float(np.sqrt(mean_squared_error(y_test, predictions))),
              'R2': float(r2_score(y_test, predictions)) if len(y_test) > 1 else float('nan')}
    results = pd.DataFrame({'actual_s': y_test.to_numpy(), 'predicted_s': predictions})
    return model, results, scores
