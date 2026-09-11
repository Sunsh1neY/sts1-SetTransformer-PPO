"""归档S4原始运行、实际后端、锁定源码及S5证据，逐文件校验归档。"""

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    evidence = root / 'runs/ppo-s5-verification-20260911/verification.json'
    verified = json.loads(evidence.read_text(encoding='utf-8'))
    assert [row['group'] for row in verified] == list('abc')
    args.output.mkdir(parents=True, exist_ok=False)
    files = set()
    for group in 'abc':
        files.update(p for p in (root / f'runs/ppo-s4-{group}-20260911').rglob('*') if p.is_file())
    for folder in ('sts', 'configs', 'scripts', 'tests', 'docs', 'patches', 'licenses'):
        files.update(p for p in (root / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    for name in ('pyproject.toml', 'README.md', 'AGENTS.md', 'eval_seeds.json', 'spec-v6.md', 'spec-v5.md', 'spec-v4.md'):
        files.add(root / name)
    files.add(evidence)
    files.add(root / 'runs/ppo-s4-20260911-launch.json')
    upstream = root / 'third_party/sts_lightspeed'
    for repo in (upstream, upstream / 'json', upstream / 'pybind11'):
        names = subprocess.check_output(['git', '-C', str(repo), 'ls-files', '-z']).decode().split('\0')
        files.update(repo / name for name in names if name and (repo / name).is_file())
    files.update((upstream / 'build').glob('*.pyd'))
    files.update((upstream / 'build').glob('*.dll'))
    files.add(upstream / 'build/CMakeCache.txt')
    files.add(upstream / 'build/build.ninja')
    manifest = {}
    archive_path = args.output / 'ppo-minimal-s5.zip'
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            data = path.read_bytes()
            name = path.relative_to(root).as_posix()
            manifest[name] = hashlib.sha256(data).hexdigest()
            archive.writestr(name, data)
        archive.writestr('s5-file-manifest.json', json.dumps(manifest, indent=2))
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        assert all(hashlib.sha256(archive.read(name)).hexdigest() == digest for name, digest in manifest.items())
    receipt = {
        'archive': archive_path.name, 'sha256': hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        'bytes': archive_path.stat().st_size, 'verified_files': len(manifest),
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        'git_status': subprocess.check_output(['git', 'status', '--short'], cwd=root, text=True).strip(),
        'note': '本地冻结归档；Python及其包、MSYS2工具链需另行准备，不宣称跨平台逐字节重建。',
    }
    (args.output / 'receipt.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(receipt, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
