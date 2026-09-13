"""由独立注册表生成后端准入；不改写public冻结契约。"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def generate():
    registry = json.loads((ROOT / "sts/env/ironclad-registry.json").read_text(encoding="utf-8"))
    contract = json.loads((ROOT / "sts/env/ironclad-expansion-contract.json").read_text(encoding="utf-8"))
    names = [r["name"] for r in registry["cards"]]
    assert len(names) == len(set(names))
    lines = ["// 自动生成：独立全卡扩展契约。", "#pragma once", "#include <array>", "namespace sts {",
             f'inline constexpr const char* IRONCLAD_OBSERVATION_SCHEMA = {json.dumps(contract["observation_schema"])};',
             f'inline constexpr const char* IRONCLAD_REGISTRY_SHA256 = "{hashlib.sha256((ROOT / "sts/env/ironclad-registry.json").read_bytes()).hexdigest()}";',
             f'inline constexpr const char* IRONCLAD_CONTRACT_SHA256 = "{hashlib.sha256((ROOT / "sts/env/ironclad-expansion-contract.json").read_bytes()).hexdigest()}";',
             f"inline constexpr std::array<const char*, {len(names)}> IRONCLAD_CARD_NAMES = {{"]
    lines += [json.dumps(name) + "," for name in names]
    lines += ["};", f"inline constexpr std::array<const char*, {len(contract['scope']['encounters'])}> IRONCLAD_ENCOUNTER_NAMES = {{"]
    lines += [json.dumps(name) + "," for name in contract["scope"]["encounters"]]
    lines += ["};", "}"]
    path = ROOT / "third_party/sts_lightspeed/bindings/ironclad-contract-config.h"
    content = "\n".join(lines) + "\n"
    if not path.exists() or path.read_text(encoding="utf-8") != content:
        path.write_text(content, encoding="utf-8")
    return path


if __name__ == "__main__":
    print(generate())
