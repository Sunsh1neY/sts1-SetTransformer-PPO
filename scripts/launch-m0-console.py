"""Compatibility entry point for the standalone battle console."""
from pathlib import Path
import runpy
if __name__=='__main__':
    runpy.run_path(str(Path(__file__).resolve().parents[1]/'tools/battle-console/launch.py'),run_name='__main__')
