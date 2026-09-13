"""固定逐牌编码枚举、容量及比较环境指纹。"""
import hashlib
import json
from pathlib import Path
import re

from sts.env.public_battle import CONTRACT_HASH, _canonical
from sts.env.real_deck import load_batch

ROOT = Path(__file__).resolve().parents[1]


def strings(file, symbol):
    text = (ROOT / "third_party/sts_lightspeed/include/constants" / file).read_text(encoding="utf-8")
    return re.findall(r'"([^"\n]*)"', text.split(symbol, 1)[1].split("};", 1)[0])


if __name__ == "__main__":
    value = {
        "schema": "comparison-battle-v2", "encoding_version": "individual-card-v1",
        "batch_sha256": load_batch()["payload_sha256"], "public_contract_sha256": CONTRACT_HASH,
        "initial_cards": 14, "card_entities": 64, "hand_slots": 10, "nonhand_slots": 64,
        "generated_per_action": 8, "truncate_at": 57, "max_actions": 512,
        "termination_rule_version": "battle-capacity-collection-v1", "reward_version": "battle_reward_v1", "gamma": 1.0,
        "player_statuses": strings("PlayerStatusEffects.h", "playerStatusStrings"),
        "enemy_statuses": strings("MonsterStatusEffects.h", "enemyStatusStrings"),
        "enemy_names": [""] + strings("MonsterIds.h", "monsterIdStrings"),
        "intent_kinds": ["NONE", "ATTACK", "ATTACK_DEFEND", "ATTACK_DEBUFF", "DEFEND", "DEFEND_BUFF", "BUFF", "DEBUFF", "SLEEP", "UNKNOWN", "ESCAPE"],
        "card_types": ["ATTACK", "SKILL", "POWER", "STATUS", "CURSE"],
    }
    value["payload_sha256"] = hashlib.sha256(_canonical(value)).hexdigest()
    path = ROOT / "sts/env/comparison-contract.json"
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path)
