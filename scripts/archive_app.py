"""Explicit historical Monza/GT7 reproduction UI, separate from Barcelona demo."""
from pathlib import Path
import os
import runpy
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ['MOTORSPORT_ML_ARCHIVE']='1'
runpy.run_path(str(ROOT/'streamlit_app.py'),run_name='__main__')
