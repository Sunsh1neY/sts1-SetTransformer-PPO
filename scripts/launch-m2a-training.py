"""Launch the approved M2a run and local TensorBoard as persistent processes."""
from pathlib import Path
import subprocess
import sys
import json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/m2a-source-context-v1'
if OUT.exists():
    raise SystemExit('Run directory already exists; refusing duplicate launch.')
logs = ROOT / 'runs/m2a-service'
logs.mkdir(parents=True, exist_ok=True)
flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_BREAKAWAY_FROM_JOB
with (logs / 'training.log').open('x', encoding='utf-8') as log:
    training = subprocess.Popen([
        sys.executable, '-B', str(ROOT / 'scripts/run-m2a-corpus-ppo.py'),
        '--backend-root', str(ROOT / 'third_party/sts_lightspeed'),
        '--output', str(OUT)], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
        creationflags=flags)
with (logs / 'tensorboard.log').open('x', encoding='utf-8') as log:
    board = subprocess.Popen([
        sys.executable, '-m', 'tensorboard.main', '--host', '127.0.0.1',
        '--port', '6006', '--reload_interval', '5', '--logdir_spec',
        f'M0:{ROOT / "runs/a-v2-ppo-v1/tensorboard/a-v2-ppo-v1"},M2a:{OUT / "tensorboard/m2a-source-context-v1"}'],
        cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, creationflags=flags)
print(json.dumps({'training_pid': training.pid, 'tensorboard_pid': board.pid,
                  'url': 'http://127.0.0.1:6006/', 'output': str(OUT)}))
