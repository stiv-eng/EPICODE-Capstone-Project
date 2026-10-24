from conftest import chart_specs
"""Streamlit script/widget checks; these do not claim visual browser inspection."""
from pathlib import Path
import importlib.abc
import sys

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def explorer_at(directory, monkeypatch):
    import motorsport_ui.telemetry as ui
    monkeypatch.setattr(ui,'ROOT',directory)
    return AppTest.from_file(str(ROOT/'pages/00_Data_Explorer.py'), default_timeout=45).run()


def test_home_starts_without_importing_fastf1_or_deep_learning(monkeypatch):
    class BlockLegacy(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split('.')[0] in {'fastf1', 'keras', 'torch'}:
                raise ImportError('Legacy imports blocked for offline startup test')
    monkeypatch.setattr(sys, 'meta_path', [BlockLegacy()] + sys.meta_path)
    app = AppTest.from_file(str(ROOT/'streamlit_app.py'), default_timeout=45).run()
    assert not app.exception
    assert app.title[0].value == 'Motorsport Telemetry Analyzer'
    assert app.checkbox[0].value is False


def test_explorer_no_local_dataset_and_upload_prompt(tmp_path,monkeypatch):
    app = explorer_at(tmp_path,monkeypatch)
    assert not app.exception
    assert any('carica un file' in i.value for i in app.info)
    app.radio[0].set_value('Carica file').run()
    assert not app.exception and len(app.get('file_uploader')) == 1


def test_missing_channels_still_plot_available_signal(tmp_path,monkeypatch):
    (tmp_path/'data/raw').mkdir(parents=True)
    pd.DataFrame({'elapsed_s': [0, 1, 2], 'speed_kmh': [50, 70, 60]}).to_csv(tmp_path/'data/raw/minimal.csv', index=False)
    app = explorer_at(tmp_path,monkeypatch)
    assert not app.exception and len(chart_specs(app)) == 1
    assert any('Canali canonici assenti' in i.value for i in app.info)
    app.multiselect[0].set_value([]).run()
    assert not app.exception
    app.radio(key='explorer_section').set_value('Position / Track Map').run()
    assert any('Track visualization unavailable' in i.value for i in app.info)


def test_manual_mapping_converts_uploaded_style_csv(tmp_path,monkeypatch):
    (tmp_path/'data/raw').mkdir(parents=True)
    pd.DataFrame({'clock': [0, 1000], 'velocity': [10, 20]}).to_csv(tmp_path/'data/raw/custom.csv', index=False)
    app = explorer_at(tmp_path,monkeypatch)
    app.selectbox(key='custom.csv_Canonical / units unspecified_elapsed_s').set_value('clock')
    app.selectbox(key='custom.csv_Canonical / units unspecified_speed_kmh').set_value('velocity')
    app.selectbox(key='custom.csv_Canonical / units unspecified_elapsed_s_unit').set_value('ms')
    app.selectbox(key='custom.csv_Canonical / units unspecified_speed_kmh_unit').set_value('m/s')
    app.button[0].click().run()
    assert not app.exception
    assert app.metric[2].value == '1.00 s'
    assert app.metric[3].value == '72.0 km/h'


@pytest.mark.skipif(not (ROOT/'data/raw/telemetry.parquet').exists(), reason='Local attachment unavailable')
def test_real_dataset_produces_telemetry_and_position_graphs(original_app):
    app = original_app(ROOT/'pages/00_Data_Explorer.py')
    assert not app.exception
    assert app.metric[0].value == '116,987'
    assert len(chart_specs(app)) == 1
    assert any('Analisi sui giri non disponibile' in i.value for i in app.caption)
    app.multiselect[0].set_value(['rpm', 'gear']).run()
    assert not app.exception
    app.radio(key='explorer_section').set_value('Position / Track Map').run()
    assert not app.exception and len(chart_specs(app))==1
