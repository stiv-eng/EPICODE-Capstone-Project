"""Offline Barcelona audit; always runs the data gate before model fitting."""
from pathlib import Path
import json

import pandas as pd

from motorsport.ml.barcelona import load_corpus,data_gate,ROOT
from scripts.download_barcelona import write_json


def audit():
    corpus,result=load_corpus()
    result['data_gate']=data_gate(corpus,result)
    write_json(ROOT/'docs/BARCELONA_AUDIT_V07.json',result)
    for name,key in [('BARCELONA_RECORDINGS_V07.csv','records'),('BARCELONA_LAPS_V07.csv','lap_audit')]:
        (ROOT/'docs'/name).write_text(pd.DataFrame(result[key]).to_csv(index=False,lineterminator='\n'),encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('records','lap_audit')},indent=2),flush=True)
    return corpus,result


if __name__=='__main__':audit()
