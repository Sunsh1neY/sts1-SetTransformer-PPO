"""从单一JSON契约生成C++常量，防止两端独立修改动作与容量。"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def generate():
    config = json.loads((ROOT / "sts/env/public-battle-contract.json").read_text(encoding="utf-8"))
    cap = config["capacity"]
    assert config["action_count"] == cap["hand"] * cap["targets"] + 1 + cap["potions"] * cap["targets"]
    assert cap["max_card_entities_bound"] == cap["max_initial_cards"] + cap["max_actions"] * cap["generated_per_action_bound"]
    constants = {
        "PUBLIC_HAND_CAPACITY": cap["hand"], "PUBLIC_TARGET_CAPACITY": cap["targets"],
        "PUBLIC_POTION_CAPACITY": cap["potions"], "PUBLIC_ACTION_COUNT": config["action_count"],
        "PUBLIC_END_TURN": config["end_turn"], "PUBLIC_MAX_ACTIONS": cap["max_actions"],
        "PUBLIC_MAX_INITIAL_CARDS": cap["max_initial_cards"],
        "PUBLIC_GENERATED_PER_ACTION": cap["generated_per_action_bound"],
    }
    lines = ["// 自动生成；请修改sts/env/public-battle-contract.json并重新运行生成器。", "#pragma once", "#include <array>", "namespace sts {"]
    lines += [f"inline constexpr int {name} = {value};" for name, value in constants.items()]
    for label, key in (("CARD", "cards"), ("POTION", "potions"), ("RELIC", "relics"), ("ENCOUNTER", "encounters")):
        names = [entry["name"] if isinstance(entry, dict) else entry for entry in config[key]]
        lines.append(f"inline constexpr std::array<const char*, {len(names)}> PUBLIC_{label}_NAMES = {{")
        lines += ["    " + json.dumps(name) + "," for name in names]
        lines.append("};")
    lines.append("}")
    target = ROOT / "third_party/sts_lightspeed/bindings/public-contract-config.h"
    content = "\n".join(lines) + "\n"
    if not target.exists() or target.read_text(encoding="utf-8") != content:
        target.write_text(content, encoding="utf-8")
    return target


if __name__ == "__main__":
    print(generate())
