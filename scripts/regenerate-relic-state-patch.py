"""Regenerate the additive relic patch against the frozen base patch chain."""
import hashlib
import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'third_party/sts_lightspeed'
FILES = ['bindings/integrated-card-env.cpp', 'include/combat/BattleContext.h',
         'src/combat/BattleContext.cpp']


def main():
    adapter = BACKEND / FILES[0]
    registry_hash = hashlib.sha256((ROOT/'sts/env/relic-state-registry.json').read_bytes()).hexdigest()
    text = adapter.read_text(encoding='utf-8')
    text, count = re.subn(r'(module.attr\("RELIC_STATE_REGISTRY_SHA256"\) = ")[a-f0-9]+',
                         lambda m: m.group(1)+registry_hash, text)
    if count != 1:
        raise ValueError('Expected one explicit relic registry fingerprint')
    adapter.write_text(text, encoding='utf-8')
    with tempfile.TemporaryDirectory() as folder:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(folder)/'index'))
        def git(*args):
            return subprocess.check_output(['git','-C',str(BACKEND),*args], env=env)
        git('read-tree','HEAD')
        for name in ('lightspeed-battle-env.patch','lightspeed-enemy-potion.patch'):
            git('apply','--cached',str(ROOT/'patches'/name))
        patch = ROOT/'patches/lightspeed-relic-state.patch'
        patch.write_bytes(git('diff','--binary','--',*FILES))
        git('apply','--cached',str(patch))
        git('diff','--exit-code','--',*FILES)
        git('apply','--reverse','--check',str(patch))
    print('Relic patch reproduces all three modified backend files from the locked base')


if __name__ == '__main__':
    main()
