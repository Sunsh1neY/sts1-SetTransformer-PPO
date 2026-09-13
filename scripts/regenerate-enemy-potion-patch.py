"""从锁定后端加冻结基础补丁重建独立增量，不改后端真实索引。"""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
BACKEND=ROOT/'third_party/sts_lightspeed'

def run(*args,env=None):
    return subprocess.check_output(['git','-C',str(BACKEND),*args],env=env)

with tempfile.TemporaryDirectory() as folder:
    env=dict(os.environ,GIT_INDEX_FILE=str(Path(folder)/'index'))
    run('read-tree','HEAD',env=env)
    run('apply','--cached',str(ROOT/'patches/lightspeed-battle-env.patch'),env=env)
    tree=run('write-tree',env=env).decode().strip()
    files=['CMakeLists.txt','bindings/slaythespire.cpp','include/combat/BattleContext.h',
           'include/combat/ActionQueue.h','include/combat/CardQueue.h','include/combat/Monster.h',
           'include/combat/CardManager.h','include/combat/Player.h','src/combat/Actions.cpp',
           'src/combat/BattleContext.cpp','src/combat/CardInstance.cpp','src/combat/CardManager.cpp',
           'src/combat/CardQueue.cpp','src/combat/Player.cpp','src/combat/Monster.cpp','src/combat/MonsterSpecific.cpp']
    data=run('diff','--binary',tree,'--',*files,env=env)
    for name in ['enemy-potion-env.cpp','enemy-potion-env.h','integrated-card-env.cpp','integrated-card-env.h','integrated-public-config.h']:
        result=subprocess.run(['git','-C',str(BACKEND),'diff','--no-index','--binary','--','NUL','bindings/'+name],capture_output=True)
        if result.returncode not in (0,1):raise RuntimeError(result.stderr.decode())
        data+=result.stdout
    target=ROOT/'patches/lightspeed-enemy-potion.patch'
    target.write_bytes(data)
    run('apply','--cached','--check',str(target),env=env)
    run('apply','--reverse','--check',str(target))
    print(target)
