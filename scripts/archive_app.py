"""Explicit historical Monza/GT7 reproduction UI, separate from Barcelona demo."""
from pathlib import Path
import os
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ['MOTORSPORT_ML_ARCHIVE']='1'
if __name__=='__main__':
    from streamlit.web.cli import main
    sys.argv=['streamlit','run',str(ROOT/'streamlit_app.py'),*sys.argv[1:]]
    raise SystemExit(main())
