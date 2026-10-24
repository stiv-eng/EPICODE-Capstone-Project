"""Explicit original-attachment UI coverage, outside the principal demo catalog."""
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest


@pytest.fixture
def original_app():
    def create(path):
        from motorsport_ui.telemetry import get_source
        source=Path(__file__).resolve().parents[1]/'data/raw/telemetry.parquet'
        if not source.exists():
            pytest.skip('Original local attachment unavailable')
        session=get_source(str(source.resolve()))
        app=AppTest.from_file(str(path),default_timeout=60)
        app.session_state['telemetry_registry']={'upload:original':session}
        app.session_state['telemetry_active_key']='upload:original'
        return app.run()
    return create


def chart_specs(app):
    """Inspect actual rendered figure payloads across native and shared components."""
    import json
    specs=[json.loads(n.proto.spec) for n in app.get('plotly_chart')]
    for node in app.get('component_instance'):
        if node.proto.component_name.endswith('motorsport_hover'):
            specs.extend(json.loads(node.proto.json_args)['specs'])
    return specs
