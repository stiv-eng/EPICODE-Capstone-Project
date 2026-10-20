"""Rete Keras per apprendere l'errore residuo di una baseline fisica."""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.metrics import mean_absolute_error
from .features import NUMERIC_FEATURES, CATEGORICAL_FEATURES, ALL_FEATURES


@dataclass
class TrainingResult:
    model: object
    preprocessor: object
    metrics: dict
    history: dict
    validation_predictions: object = None


def _keras():
    # Keras 3 con backend selezionabile: torch di default; puo' usare tensorflow.
    os.environ.setdefault('KERAS_BACKEND', 'torch')
    import keras
    return keras


def fit_model(dataset, epochs=35, seed=42):
    """Lo split e' PER GIRO, non per riga: nessuno snapshot si duplica fra split."""
    groups = dataset['lap_uid'].astype(str)
    if groups.nunique() < 8:
        raise ValueError('Servono almeno 8 giri FP validi per effettuare un train/validation split affidabile.')
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed)
    train_idx, valid_idx = next(splitter.split(dataset, groups=groups))
    train = dataset.iloc[train_idx]
    valid = dataset.iloc[valid_idx]
    prep = ColumnTransformer([
        ('numeric', StandardScaler(), NUMERIC_FEATURES),
        ('categorical', OneHotEncoder(handle_unknown='ignore', sparse_output=False), CATEGORICAL_FEATURES),
    ])
    x_train = np.asarray(prep.fit_transform(train[ALL_FEATURES]), dtype='float32')
    x_valid = np.asarray(prep.transform(valid[ALL_FEATURES]), dtype='float32')
    y_train = train['target_residual_s'].to_numpy(dtype='float32')
    y_valid = valid['target_residual_s'].to_numpy(dtype='float32')

    keras = _keras()
    keras.utils.set_random_seed(seed)
    net = keras.Sequential([
        keras.layers.Input(shape=(x_train.shape[1],)),
        keras.layers.Dense(64, activation='relu'),
        keras.layers.Dropout(0.1),
        keras.layers.Dense(32, activation='relu'),
        keras.layers.Dense(1),
    ])
    net.compile(optimizer=keras.optimizers.Adam(learning_rate=0.001), loss=keras.losses.Huber())
    callback = keras.callbacks.EarlyStopping(monitor='val_loss', patience=7, restore_best_weights=True)
    training = net.fit(x_train, y_train, validation_data=(x_valid, y_valid),
                       epochs=epochs, batch_size=64, callbacks=[callback], verbose=0)
    residual = net.predict(x_valid, verbose=0).reshape(-1)
    pred = valid['baseline_s'].to_numpy() + residual
    valid_predictions = valid[['lap_uid', 'session', 'driver', 'progress', 'elapsed_s', 'actual_s', 'baseline_s']].copy()
    valid_predictions['prediction_s'] = np.maximum(valid_predictions['elapsed_s'].to_numpy(), pred)
    valid_predictions['abs_error_s'] = np.abs(valid_predictions['actual_s']-valid_predictions['prediction_s'])
    # La metrica macro considera ogni giro una sola volta (evita che snapshot multipli
    # dello stesso giro facciano apparire la validazione piu' robusta del reale).
    macro_keras = valid_predictions.groupby('lap_uid')['abs_error_s'].mean().mean()
    macro_baseline = valid_predictions.assign(err=np.abs(valid_predictions['actual_s']-valid_predictions['baseline_s'])).groupby('lap_uid')['err'].mean().mean()
    metrics = {
        'validation_macro_baseline_mae_s': float(macro_baseline),
        'validation_macro_keras_mae_s': float(macro_keras),
        'validation_baseline_mae_s': float(mean_absolute_error(valid['actual_s'], valid['baseline_s'])),
        'validation_keras_mae_s': float(mean_absolute_error(valid['actual_s'], pred)),
        'train_laps': int(train['lap_uid'].nunique()),
        'validation_laps': int(valid['lap_uid'].nunique()),
        'train_snapshots': int(len(train)),
        'validation_snapshots': int(len(valid)),
    }
    return TrainingResult(net, prep, metrics, dict(training.history), valid_predictions)


def replay_predictions(lap, reference, trained):
    """Calcola la sequenza predittiva: nessuna feature usa la durata finale prima del finish."""
    from .features import snapshots
    trace = snapshots(lap, reference, include_finish=True)
    if trace.empty:
        raise ValueError('Impossibile ricostruire il replay del giro selezionato.')
    x = trained.preprocessor.transform(trace[ALL_FEATURES])
    residual = trained.model.predict(np.asarray(x, dtype='float32'), verbose=0).reshape(-1)
    trace['prediction_s'] = np.maximum(trace['elapsed_s'].to_numpy(), trace['baseline_s'].to_numpy() + residual)
    trace.loc[trace['is_finish'], 'prediction_s'] = trace.loc[trace['is_finish'], 'actual_s']
    return trace


def save_model_artifacts(trained, output_dir, metadata=None):
    """Salva modello e preprocessing, separati e versionati per weekend."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    trained.model.save(str(path / 'residual_model.keras'))
    joblib.dump(trained.preprocessor, path / 'preprocessor.joblib')
    (path / 'metrics.json').write_text(json.dumps({
        'metrics': trained.metrics, 'metadata': metadata or {},
    }, indent=2), encoding='utf-8')
    return path


def load_model_artifacts(output_dir):
    path = Path(output_dir)
    keras = _keras()
    model = keras.models.load_model(str(path / 'residual_model.keras'))
    preprocessor = joblib.load(path / 'preprocessor.joblib')
    saved = json.loads((path / 'metrics.json').read_text(encoding='utf-8'))
    return TrainingResult(model, preprocessor, saved['metrics'], {})


def evaluate_qualifying(laps, references, trained):
    """Valutazione storica out-of-sample rispetto alle FP del medesimo weekend.

    Le label Q si usano SOLO dopo la predizione, per misurare gli errori.
    Esclude lo snapshot del traguardo, che per definizione rivela la label.
    Le metriche considerano ciascun giro separatamente.
    """
    from .features import snapshots
    tables = [snapshots(lap, references[lap.driver], include_finish=False)
              for lap in laps if lap.driver in references]
    tables = [table for table in tables if not table.empty]
    if not tables:
        raise ValueError('Nessun giro Q valutabile con i riferimenti FP3 disponibili.')
    frame = pd.concat(tables, ignore_index=True)
    x = trained.preprocessor.transform(frame[ALL_FEATURES])
    residuals = trained.model.predict(np.asarray(x, dtype='float32'), verbose=0).reshape(-1)
    frame['prediction_s'] = np.maximum(frame['elapsed_s'], frame['baseline_s'] + residuals)
    frame['baseline_error_s'] = (frame['baseline_s'] - frame['actual_s']).abs()
    frame['keras_error_s'] = (frame['prediction_s'] - frame['actual_s']).abs()
    frame['gain_s'] = frame['baseline_error_s'] - frame['keras_error_s']
    frame['stage'] = pd.cut(frame['progress'], bins=[0, .25, .50, .75, 1.01],
                            labels=['0–25%', '25–50%', '50–75%', '75–100%'],
                            include_lowest=True)
    return frame


def summarize_qualifying(frame):
    """MAE macro per giro e per fase, evitando di contare lo stesso giro piu' volte."""
    lap = (frame.groupby('lap_uid').agg(driver=('driver','first'),
            actual_s=('actual_s','first'), snapshots=('progress','size'),
            baseline_mae_s=('baseline_error_s','mean'),
            keras_mae_s=('keras_error_s','mean')).reset_index())
    # observed=True evita combinazioni vuote di bucket categorici.
    by_stage = (frame.groupby(['lap_uid', 'stage'], observed=True)
            .agg(baseline_mae_s=('baseline_error_s', 'mean'),
                 keras_mae_s=('keras_error_s', 'mean')).reset_index()
            .groupby('stage', observed=True)[['baseline_mae_s','keras_mae_s']].mean().reset_index())
    metrics = {
        'laps': int(len(lap)),
        'baseline_macro_mae_s': float(lap['baseline_mae_s'].mean()),
        'keras_macro_mae_s': float(lap['keras_mae_s'].mean()),
        'improvement_s': float(lap['baseline_mae_s'].mean()-lap['keras_mae_s'].mean()),
    }
    return metrics, lap, by_stage
