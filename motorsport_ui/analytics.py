"""Metriche pure, utilizzabili anche da test e notebook, senza Streamlit."""
import numpy as np
import pandas as pd


def clean_lap_table(laps):
    """Normalizza lap times / stint / tyres; non inventa informazioni mancanti."""
    frame = pd.DataFrame(laps).copy()
    if frame.empty:
        return frame
    required = ['LapTime', 'Driver', 'LapNumber']
    if any(col not in frame for col in required):
        return pd.DataFrame()
    frame = frame.loc[frame['LapTime'].notna() & frame['Driver'].notna()].copy()
    if 'Deleted' in frame:
        frame = frame.loc[~frame['Deleted'].fillna(False).astype(bool)]
    if 'IsAccurate' in frame:
        frame = frame.loc[frame['IsAccurate'].fillna(False).astype(bool)]
    frame['LapTimeSeconds'] = pd.to_timedelta(frame['LapTime']).dt.total_seconds()
    frame = frame.loc[frame['LapTimeSeconds'].between(40, 250)].copy()
    for col in ['Stint', 'TyreLife']:
        if col not in frame:
            frame[col] = np.nan
    if 'Compound' not in frame:
        frame['Compound'] = 'UNKNOWN'
    frame['Compound'] = frame['Compound'].fillna('UNKNOWN').astype(str)
    return frame.sort_values(['Driver', 'LapNumber'])


def driver_summary(frame):
    if frame.empty:
        return pd.DataFrame()
    grouped = frame.groupby('Driver')['LapTimeSeconds']
    result = grouped.agg(best='min', median='median', mean='mean', std='std', laps='count')
    result['consistency_std_s'] = result['std'].fillna(0)
    return result.reset_index().sort_values('best')


def stint_summary(frame):
    if frame.empty:
        return pd.DataFrame()
    data = frame.copy()
    data['Stint'] = data['Stint'].fillna(-1)
    return (data.groupby(['Driver', 'Stint', 'Compound'], dropna=False)
            .agg(first_lap=('LapNumber', 'min'), last_lap=('LapNumber', 'max'),
                 flying_laps=('LapNumber', 'count'), best_s=('LapTimeSeconds', 'min'),
                 avg_s=('LapTimeSeconds', 'mean'))
            .reset_index().sort_values(['Driver', 'first_lap']))


def degradation_regression(frame, min_points=3):
    """Regressione lineare su TyreLife per ciascuno stint, non confronto causale.

    Ritorna pendenza s/giro e R²; il carico carburante e il traffico non sono controllati.
    """
    if frame.empty:
        return pd.DataFrame()
    result = []
    for (driver, stint), group in frame.dropna(subset=['TyreLife', 'Stint']).groupby(['Driver', 'Stint']):
        group = group.dropna(subset=['LapTimeSeconds']).sort_values('TyreLife')
        if len(group) < min_points or group['TyreLife'].nunique() < 2:
            continue
        x = group['TyreLife'].to_numpy(dtype=float)
        y = group['LapTimeSeconds'].to_numpy(dtype=float)
        slope, intercept = np.polyfit(x, y, 1)
        y_hat = slope*x + intercept
        sst = float(np.sum((y-y.mean())**2))
        r2 = 1-float(np.sum((y-y_hat)**2))/sst if sst > 0 else np.nan
        result.append({'Driver': str(driver), 'Stint': int(stint), 'Compound': str(group['Compound'].iloc[0]),
                       'laps': len(group), 'slope_s_per_tyre_lap': float(slope),
                       'intercept_s': float(intercept), 'r2': r2})
    return pd.DataFrame(result)


def sampled_car_data(lap):
    """Telemetria giro con distanza e tempo di giro; non interpola campioni futuri."""
    car = lap.get_car_data().add_distance().copy()
    if car.empty:
        return pd.DataFrame()
    columns = ['Distance', 'Time', 'Speed', 'Throttle', 'Brake', 'RPM', 'nGear']
    for col in columns:
        if col not in car:
            car[col] = np.nan
    car = car[columns].copy()
    car['elapsed_s'] = (pd.to_timedelta(car['Time']) - pd.to_timedelta(car['Time']).iloc[0]).dt.total_seconds()
    car['Distance'] = pd.to_numeric(car['Distance'], errors='coerce')
    car = car.replace([np.inf, -np.inf], np.nan).dropna(subset=['Distance', 'Speed', 'elapsed_s'])
    return car.sort_values('Distance').drop_duplicates('Distance').reset_index(drop=True)


def telemetry_delta(reference, comparison):
    """Delta cumulato interpolato a distanza sul giro riferimento.

    Delta positivo: il giro confronto impiega piu' tempo per coprire la distanza.
    Limiti: telemetria FastF1 e distanze integrate possono differire tra giri.
    """
    if reference.empty or comparison.empty:
        return pd.DataFrame()
    a = reference[['Distance', 'elapsed_s']].drop_duplicates('Distance').sort_values('Distance')
    b = comparison[['Distance', 'elapsed_s']].drop_duplicates('Distance').sort_values('Distance')
    hi = min(float(a['Distance'].iloc[-1]), float(b['Distance'].iloc[-1]))
    d = a.loc[a['Distance'] <= hi, 'Distance'].to_numpy(dtype=float)
    if len(d) < 2:
        return pd.DataFrame()
    t1 = np.interp(d, a['Distance'], a['elapsed_s'])
    t2 = np.interp(d, b['Distance'], b['elapsed_s'])
    return pd.DataFrame({'Distance': d, 'delta_s': t2-t1})