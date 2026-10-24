"""Offline Plotly component with a reserved readout outside the plotted signals.

Plotly's native hoverlabel has no fixed outside-panel placement. This small HTML
component uses the installed Plotly bundle, disables only floating labels and
listens to the public plotly_hover event. No CDN or frontend package is added.
"""
from functools import lru_cache
from pathlib import Path

from plotly.offline import get_plotlyjs
import streamlit.components.v1 as components


@lru_cache(maxsize=1)
def component_template():
    return Path(__file__).with_name('comparison_hover.html').read_text(encoding='utf-8')


def comparison_document(figure):
    # Escape untrusted labels/channel names before inserting JSON into a script.
    payload=figure.to_json().replace('<','\\u003c')
    return component_template().replace('/*PLOTLY_BUNDLE*/',get_plotlyjs()).replace('/*FIGURE_JSON*/',payload)


def render_comparison(figure):
    components.html(comparison_document(figure),height=int(figure.layout.height)+12,scrolling=False)
