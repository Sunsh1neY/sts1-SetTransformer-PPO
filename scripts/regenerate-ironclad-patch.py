"""从冻结public补丁及独立后端修改生成可重建的增量补丁。"""
from pathlib import Path
import difflib
import subprocess

ROOT=Path(__file__).resolve().parents[1]
BACKEND=ROOT/'third_party/sts_lightspeed'


def regenerate():
    base=(ROOT/'patches/lightspeed-battle-env.patch').read_text(encoding='utf-8')
    part=base.split('diff --git a/bindings/public-battle-env.cpp b/bindings/public-battle-env.cpp\n')[1].split('\ndiff --git ')[0]
    original=''.join(line[1:]+'\n' for line in part.splitlines() if line.startswith('+') and not line.startswith('+++'))
    actual=(BACKEND/'bindings/public-battle-env.cpp').read_text(encoding='utf-8')
    patch='diff --git a/bindings/public-battle-env.cpp b/bindings/public-battle-env.cpp\n'
    patch+=''.join(difflib.unified_diff(original.splitlines(True),actual.splitlines(True),fromfile='a/bindings/public-battle-env.cpp',tofile='b/bindings/public-battle-env.cpp'))
    # 这两份public修复保持冻结，避免把基线修复重复放进增量补丁。
    patch+=subprocess.check_output(['git','diff','--','src','include',
                                  ':(exclude)include/constants/Cards.h',
                                  ':(exclude)src/combat/MonsterSpecific.cpp'],cwd=BACKEND).decode('utf-8')
    (ROOT/'patches/lightspeed-ironclad-expansion.patch').write_text(patch,encoding='utf-8')


if __name__=='__main__':regenerate()
