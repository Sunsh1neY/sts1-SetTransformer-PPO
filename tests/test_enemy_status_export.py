"""直接编译生产状态导出函数的C++夹具；不是完整遭遇或共享模型验收。"""
import json
import os
from pathlib import Path
import subprocess


def test_approved_status_export_preserves_zero_and_boolean(tmp_path):
    root = Path(__file__).resolve().parents[1]
    backend = root / 'third_party/sts_lightspeed'
    source = (backend / 'bindings/enemy-potion-env.cpp').read_text(encoding='utf-8')
    # 编译原生产函数体，避免另写一个Python等价实现形成自证。
    function = source.split('Json monsterStatuses(const Monster &m) {', 1)[1].split('int potionPotency', 1)[0]
    program = '#include <iostream>\n#include <nlohmann/json.hpp>\n#include "combat/Monster.h"\nusing namespace sts;\nusing Json=nlohmann::json;\n'
    program += 'Json monsterStatuses(const Monster &m) {' + function
    program += 'int main(){ Json all=Json::array();'
    for status, amount in [('FLIGHT',3),('THORNS',3),('SLOW',0),('INTANGIBLE',1),('FADING',5),('SHIFTING',1),('REACTIVE',1),('TIME_WARP',11)]:
        program += '{Monster m; m.setHasStatus<MS::' + status + '>(true); m.setStatus<MS::' + status + '>(' + str(amount) + '); all.push_back(monsterStatuses(m));}'
    program += '{Monster m; all.push_back(monsterStatuses(m));} std::cout << all.dump();}'
    cpp = tmp_path/'probe.cpp'; cpp.write_text(program,encoding='utf-8')
    binary=tmp_path/'probe.exe'; env=dict(os.environ); env['PATH']='C:/msys64/mingw64/bin;'+env['PATH']
    result=subprocess.run(['C:/msys64/mingw64/bin/g++.exe','-std=c++17','-O0',str(cpp),'-I'+str(backend/'include'),'-I'+str(backend/'json/single_include'),'-o',str(binary)],capture_output=True,text=True,env=env)
    assert result.returncode==0,result.stderr
    result=subprocess.run([str(binary)],capture_output=True,text=True,env=env,check=True)
    assert json.loads(result.stdout)==[{'Flight':3},{'Thorns':3},{'Slow':0},{'Intangible':1},{'Fading':5},{'Shifting':1},{'Reactive':1},{'Time Warp':11},{}]
