"""把150版本证据账本写成可审阅的75行完成表。"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'sts/env/ironclad-expansion-coverage.json').read_text(encoding='utf-8'))['versions']
names=sorted({r['name'] for r in data})
assert len(names)==75 and len(data)==150 and all(r['expanded_admitted'] for r in data)
lines=['# 全战士卡牌完成表','', '2026-09-13；75类、150版本。通过表示当前具名环境的工程准入，不表示任意组合穷尽或正式训练成绩。完整范围见[验收报告](ironclad-full-cards-report.md)。','', '| 卡牌 | 基础 | 升级 | 证据入口 |','|---|---|---|---|']
for name in names:
    rows=sorted([r for r in data if r['name']==name],key=lambda r:r['upgrade_count'])
    assert [r['upgrade_count'] for r in rows]==[0,1]
    evidence=sorted({p for row in rows for p in row['evidence']})
    for path in evidence:assert (ROOT/path).exists(),path
    links='、'.join(f'[{Path(p).name}](../{p})' for p in evidence)
    lines.append(f'| {name} | 已准入 | 已准入 | {links} |')
(ROOT/'docs/ironclad-full-card-coverage.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('75类150版本完成表及证据路径校验通过')
