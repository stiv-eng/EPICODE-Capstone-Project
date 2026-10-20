"""Acquisizione FastF1. Nessun dato Q e' usato per il training."""
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd


@dataclass
class LapRecord:
    uid: str
    driver: str
    session: str
    lap_number: int
    lap_time_s: float
    compound: str
    tyre_life: float
    telemetry: pd.DataFrame


def seconds(value):
    if pd.isna(value):
        return np.nan
    return pd.Timedelta(value).total_seconds()


def normalize_telemetry(raw):
    """Distanza integrata causalmente dalla velocita': non usa lunghezza futura del giro."""
    if raw.empty or not {'Time', 'Speed'}.issubset(raw.columns):
        return pd.DataFrame()
    out = raw.copy()
    out['elapsed_s'] = pd.to_timedelta(out['Time']).dt.total_seconds()
    cols = ['elapsed_s', 'Speed', 'Throttle', 'Brake', 'RPM', 'nGear']
    for col in cols:
        if col not in out:
            out[col] = 0
    out = out[cols].copy()
    for col in cols:
        out[col] = pd.to_numeric(out[col], errors='coerce')
    out = out.replace([np.inf, -np.inf], np.nan).dropna(subset=['elapsed_s', 'Speed'])
    out = out.sort_values('elapsed_s').drop_duplicates('elapsed_s', keep='last')
    if len(out) < 10:
        return pd.DataFrame()
    out[['Throttle', 'Brake', 'RPM', 'nGear']] = out[['Throttle', 'Brake', 'RPM', 'nGear']].ffill().fillna(0)
    # get_car_data.Time puo' non iniziare esattamente a zero nel giro.
    # L'origine di ogni osservazione e' fissata al primo campione disponibile.
    out['elapsed_s'] -= float(out['elapsed_s'].iloc[0])
    t = out['elapsed_s'].to_numpy(dtype=float)
    v = out['Speed'].to_numpy(dtype=float) / 3.6
    dt = np.maximum(np.diff(t), 0)
    distance = np.r_[0.0, np.cumsum(np.maximum((v[:-1] + v[1:]) / 2, 0) * dt)]
    out['distance_m'] = distance
    return out.reset_index(drop=True)


def _load_session(year, event, code, cache_dir):
    import fastf1
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(cache_dir))
    session = fastf1.get_session(year, event, code)
    session.load(laps=True, telemetry=True, weather=False, messages=False)
    return session


def extract_laps(session, code, max_per_driver=None):
    """Seleziona giri validi, ordinandoli per tempo. max_per_driver=None conserva tutti."""
    laps = session.laps.copy()
    laps = laps.loc[laps['LapTime'].notna() & laps['Driver'].notna()]
    if 'IsAccurate' in laps:
        laps = laps.loc[laps['IsAccurate'].fillna(False).astype(bool)]
    if 'Deleted' in laps:
        laps = laps.loc[~laps['Deleted'].fillna(False).astype(bool)]
    laps = laps.sort_values('LapTime')
    if max_per_driver is not None:
        laps = laps.groupby('Driver', sort=False).head(max_per_driver)
    result = []
    for _, lap in laps.iterrows():
        try:
            car = normalize_telemetry(lap.get_car_data())
            lap_time = seconds(lap['LapTime'])
            if car.empty or not 40 < lap_time < 250 or car['distance_m'].iloc[-1] < 1000:
                continue
            driver = str(lap['Driver'])
            number = int(lap['LapNumber'])
            compound = str(lap.get('Compound', 'UNKNOWN'))
            tyre_life = pd.to_numeric(lap.get('TyreLife', 0), errors='coerce')
            result.append(LapRecord(
                uid=f'{code}:{driver}:{number}', driver=driver, session=code,
                lap_number=number, lap_time_s=float(lap_time), compound=compound,
                tyre_life=float(tyre_life) if pd.notna(tyre_life) else 0.0,
                telemetry=car,
            ))
        except (KeyError, ValueError, IndexError, TypeError):
            continue
    return result


def load_practice(year, event, cache_dir='.fastf1_cache', max_per_driver=3):
    """FP3 reference piu' veloce per pilota; dataset unico FP1+FP2+FP3."""
    all_laps = []
    fp3_refs = {}
    counts = {}
    for code in ['FP1', 'FP2', 'FP3']:
        session = _load_session(year, event, code, cache_dir)
        selected = extract_laps(session, code, max_per_driver=max_per_driver)
        counts[code] = len(selected)
        all_laps.extend(selected)
        if code == 'FP3':
            for lap in selected:
                if lap.driver not in fp3_refs or lap.lap_time_s < fp3_refs[lap.driver].lap_time_s:
                    fp3_refs[lap.driver] = lap
    if not fp3_refs:
        raise ValueError('Nessun riferimento FP3 valido; il weekend potrebbe non avere FP3.')
    # Evita leakage: il giro FP3 usato come riferimento non entra nei campioni
    # train/validazione, altrimenti il suo label sarebbe noto dalla baseline.
    eligible = [lap for lap in all_laps if lap.driver in fp3_refs
                and lap.uid != fp3_refs[lap.driver].uid]
    if not eligible:
        raise ValueError('Non sono stati trovati giri FP compatibili con le FP3.')
    return eligible, fp3_refs, counts


def load_qualifying(year, event, cache_dir='.fastf1_cache', max_per_driver=5):
    session = _load_session(year, event, 'Q', cache_dir)
    return extract_laps(session, 'Q', max_per_driver=max_per_driver)
