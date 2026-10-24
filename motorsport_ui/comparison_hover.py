"""Compatibility entrypoint; production rendering uses the shared hover component.

``comparison_document`` remains a standalone offline export/test helper. The app
uses the cacheable runtime and event implementation in hover.py / hover.html.
"""
from functools import lru_cache
from pathlib import Path

from plotly.offline import get_plotlyjs


@lru_cache(maxsize=1)
def component_template():
    return Path(__file__).with_name('hover.html').read_text(encoding='utf-8')


def comparison_document(figure):
    from .hover import prepare_figure
    # Escape untrusted labels/channel names before inserting JSON into a script.
    payload=prepare_figure(figure,'time').to_json().replace('<','\\u003c')
    document=component_template().replace('</head>','<script>'+get_plotlyjs()+'</script></head>')
    bootstrap='<script id="comparison-data" type="application/json">'+payload+'</script>'
    bootstrap+="<script>window.dispatchEvent(new MessageEvent('message',{source:window.parent,data:{type:'streamlit:render',args:{specs:[JSON.parse(document.getElementById('comparison-data').textContent)]}}}));</script>"
    return document.replace('</body>',bootstrap+'</body>')


def render_comparison(figure):
    from .hover import render_chart
    render_chart(figure,mode='time',key='comparison_hover')
