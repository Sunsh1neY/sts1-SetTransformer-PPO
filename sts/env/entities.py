"""共享统一实体编码与候选接口；槽位和一次性凭据仅在模型外路由。"""
from __future__ import annotations

import copy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from sts.env.public_battle import _canonical, _integer, _reject_hidden_fields
from sts.env.selection import CARD_FIELDS

CONTRACT_PATH = Path(__file__).parents[1] / "models/unified-entity-contract.json"
CONTRACT = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
CONTRACT_HASH = hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest()
TYPES = CONTRACT["types"]
KINDS = CONTRACT["action_kinds"]
REGIONS = CONTRACT["regions"]
CARD_IDS = {r["name"]: r["id"] for r in CONTRACT["cards"]}
CARD_NUMERIC = CONTRACT["card_numeric_scales"]
CARD_BOOL = CONTRACT["card_boolean_fields"]
PLAYER_NUMERIC = CONTRACT["player_numeric_scales"]
HISTORY_NUMERIC = CONTRACT["history_numeric_fields"]
CANDIDATE_CONTEXT = CONTRACT["candidate_context"]
CANDIDATE_CONTEXT_DIM = CANDIDATE_CONTEXT["dimension"]
RESOLUTION_MODES = CANDIDATE_CONTEXT["source_modes"]
DEFAULT_CANDIDATE_CONTEXT = (0.0,) * CANDIDATE_CONTEXT_DIM


def exact(obj, keys):
    if set(obj) != set(keys):
        raise ValueError(f"实体语义字段变化：{set(obj) ^ set(keys)}")


def number(value, scale=1):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.integer, np.floating)):
        raise TypeError("语义数值类型错误")
    result = float(value) / scale
    if not np.isfinite(result):
        raise ValueError("非有限语义数值")
    return result


def boolean(value):
    if not isinstance(value, (bool, np.bool_)):
        raise TypeError("语义布尔类型错误")
    return float(value)


def onehot(value, choices):
    if value not in choices:
        raise ValueError(f"词表未登记：{value}")
    return [float(value == choice) for choice in choices]


def resolution_context_features(value):
    """把公开结算上下文变成候选特征；不进入任何普通实体token。"""
    exact(value, set(CANDIDATE_CONTEXT["fields"]))
    count = _integer(value["pending_replay_count"], "pending_replay_count")
    if count < 0 or count > 10:
        raise ValueError("待处理重复动作数量超出公开队列汇总边界")
    return (onehot(value["source_mode"], RESOLUTION_MODES) +
            [boolean(value["source_will_exhaust"]),
             number(count, CANDIDATE_CONTEXT["pending_replay_count_scale"])])


def status_features(values, vocabulary):
    if set(values) - set(vocabulary):
        raise ValueError("出现未登记的状态，必须扩充共享契约")
    return [v for name in vocabulary for v in (float(name in values), number(values.get(name, 0), 10))]


def card_features(card, region):
    exact(card, CARD_FIELDS | ({"known_top", "recovery_cost"} & set(card)))
    _integer(card["card_id"], "卡牌语义ID")
    if _integer(card["upgrade_count"], "升级次数") < 0:
        raise ValueError("升级次数不能为负")
    if CARD_IDS.get(card["name"]) != card["card_id"]:
        raise ValueError("卡牌语义ID与名称不一致")
    card = dict(card)
    card["pay_cost"] = (card["effective_cost"] if region == "hand" else card["printed_cost"]) if card["cost_kind"] == "ENERGY" else 0
    card["recovery_cost"] = card.get("recovery_cost", card["cost"] if region == "hand" else card["base_cost"])
    card["known_top"] = card.get("known_top", False)
    if card["known_top"] and region != "draw_pile":
        raise ValueError("已知顶牌只能在抽牌堆")
    return ([number(card[k], scale) for k, scale in CARD_NUMERIC.items()] +
            [boolean(card[k]) for k in CARD_BOOL] +
            onehot(card["card_id"], range(81)) + onehot(card["card_type"], CONTRACT["card_types"]) +
            onehot(card["target_kind"], ["NO_TARGET", "ENEMY"]) +
            onehot(card["cost_kind"], ["ENERGY", "X", "UNPLAYABLE"]) +
            onehot(region, REGIONS))


FEATURE_DIMS = {
    "CARD": len(CARD_NUMERIC) + len(CARD_BOOL) + 81 + len(CONTRACT["card_types"]) + 2 + 3 + len(REGIONS),
    "ENEMY": len(CONTRACT["enemy_phases"]) + 2 + 5 + len(CONTRACT["enemy_names"]) + len(CONTRACT["intent_kinds"]) + 3 * (len(CONTRACT["enemy_move_ids"]) + 1) + 2 * len(CONTRACT["enemy_statuses"]) + 3,
    "POTION": len(CONTRACT["potions"]) + 1 + 1 + 2 + len(CONTRACT["potion_regions"]),
    "RELIC": len(CONTRACT["relics"]) + 2,
    "PLAYER_GLOBAL": len(PLAYER_NUMERIC) + 2 * len(CONTRACT["player_statuses"]) + 1 + 2 + len(CONTRACT["selection_kinds"]) + 2,
}


if FEATURE_DIMS != CONTRACT["feature_dimensions"]:
    raise ValueError("统一实体字段维度与契约不一致")


@dataclass
class EntityToken:
    entity_type: str
    features: np.ndarray


@dataclass(frozen=True)
class Candidate:
    kind: str
    source: int
    target: int
    legal: bool
    context: tuple[float, ...] = DEFAULT_CANDIDATE_CONTEXT


@dataclass
class EntitySample:
    tokens: list[EntityToken]
    edges: np.ndarray
    candidates: list[Candidate]
    routes: list
    held_card_index: np.ndarray | None = None

    def permuted(self, order):
        order = list(order)
        if sorted(order) != list(range(len(self.tokens))):
            raise ValueError("必须提供完整实体置换")
        inverse = {old: new for new, old in enumerate(order)}
        remap = lambda i: -1 if i == -1 else inverse[i]
        return EntitySample([self.tokens[i] for i in order], self.edges[order][:, order].copy(),
                            [Candidate(c.kind, remap(c.source), remap(c.target), c.legal, c.context) for c in self.candidates],
                            copy.deepcopy(self.routes), np.array([remap(int(self.held_card_index[i])) for i in order], dtype=np.int64) if self.held_card_index is not None else None)


def encode_observation(obs, *, relic_encoder=None, card_encoder=None, feature_dims=None):
    """适配当前具名战斗观测；新增机制必须显式提供合法性和完整字段。"""
    dimensions = FEATURE_DIMS if feature_dims is None else feature_dims
    from sts.env.ironclad import CONTRACT as RUNTIME
    _reject_hidden_fields(obs)
    expected = {"schema", "hand", "draw_pile", "discard_pile", "exhaust_pile", "resolving",
                "player", "enemies", "potions", "potion_capacity", "relics", "action_mask", "decision", "stasis", "relations", "routing"}
    exact(obs, expected | ({"offers", "resolving_potions"} & set(obs)))
    if obs["schema"] != RUNTIME["observation_schema"]:
        raise ValueError("统一实体适配器的观测版本不匹配")
    normal_mask = np.asarray(obs["action_mask"])
    if normal_mask.dtype != np.bool_ or normal_mask.shape != (66,):
        raise ValueError("环境必须提供66位布尔普通动作mask")
    card_rows = [obs.get("offers", []) if zone == "offer" else obs[zone] for zone in REGIONS]
    if any(not isinstance(rows, list) for rows in card_rows):
        raise ValueError("牌区必须提供完整实体列表")
    count = sum(len(rows) for rows in card_rows) + len(obs["relics"]) + 1
    count += sum(bool(row["present"]) for row in obs["enemies"] + obs["potions"] + obs.get("resolving_potions", []))
    if count > CONTRACT["resources"]["max_entities"]:
        raise ValueError("总实体超出资源边界；拒绝在分配关系矩阵前继续")
    tokens, refs, cards = [], {}, []

    def add(entity_type, features):
        row = np.asarray(features, dtype=np.float32)
        if row.shape != (dimensions[entity_type],) or not np.isfinite(row).all():
            raise ValueError(f"{entity_type}字段布局或数值错误：{row.shape}")
        tokens.append(EntityToken(entity_type, row))
        return len(tokens) - 1

    for region in REGIONS:
        rows = obs.get("offers", []) if region == "offer" else obs[region]
        if region == "hand" and len(rows) > 10:
            raise ValueError("手牌超过后端路由容量")
        for i, card in enumerate(rows):
            if region == "stasis":
                exact(card, {"name"})
                if card["name"] not in CARD_IDS: raise ValueError("未知扣牌身份")
                # stasis区域是统一未知掩码：只激活公开身份与区域，其余非真实零值。
                feature = [0.] * (len(CARD_NUMERIC) + len(CARD_BOOL)) + onehot(CARD_IDS[card["name"]], range(81))
                feature += [0.] * (len(CONTRACT["card_types"]) + 2 + 3) + onehot(region, REGIONS)
                if card_encoder is not None:
                    feature.insert(len(CARD_NUMERIC) + CARD_BOOL.index("known_top") + 1, 0.0)
                refs[(region, i)] = add("CARD", feature)
                continue
            refs[(region, i)] = add("CARD", (card_encoder or card_features)(card, region))
            if len(card["damage_by_target"]) != 5:
                raise ValueError("目标预览缺行")
            cards.append((refs[(region, i)], card))
    if len(obs["enemies"]) != 5 or len(obs["potions"]) != 3:
        raise ValueError("当前后端槽位容量已变化，需要新适配器")
    for i, enemy in enumerate(obs["enemies"]):
        exact(enemy, {"name", "present", "targetable", "hp", "max_hp", "block", "intent_damage", "intent_hits", "intent_kind", "public_history", "statuses", "intent_history", "intent_history_valid", "phase"})
        if not boolean(enemy["present"]):
            if enemy["targetable"]:
                raise ValueError("不存在的敌人不能成为目标")
            continue
        history = enemy["public_history"]
        exact(history, set(HISTORY_NUMERIC))
        features = onehot(enemy["phase"], CONTRACT["enemy_phases"]) + [boolean(enemy[k]) for k in ("present", "targetable")]
        features += [number(enemy[k], 5 if k == "intent_hits" else 100) for k in ("hp", "max_hp", "block", "intent_damage", "intent_hits")]
        features += onehot(enemy["name"], CONTRACT["enemy_names"]) + onehot(enemy["intent_kind"], CONTRACT["intent_kinds"])
        features += status_features(enemy["statuses"], CONTRACT["enemy_statuses"])
        features += [number(history[k], 50) for k in HISTORY_NUMERIC]
        if len(enemy["intent_history"]) != 3 or len(enemy["intent_history_valid"]) != 3:
            raise ValueError("意图历史必须有三个位置")
        for move, valid in zip(enemy["intent_history"], enemy["intent_history_valid"]):
            move = _integer(move, "意图类别")
            if boolean(valid) != float(move != 0):
                raise ValueError("历史编号与有效性不一致")
            features += onehot(move, CONTRACT["enemy_move_ids"]) + [boolean(valid)]
        refs[("enemy", i)] = add("ENEMY", features)
    potion_names = [r["name"] for r in CONTRACT["potions"]]
    potion_rows = [("potion", "inventory", i, potion) for i, potion in enumerate(obs["potions"])]
    potion_rows += [("resolving_potion", "resolving", i, potion) for i, potion in enumerate(obs.get("resolving_potions", []))]
    for route_zone, lifecycle, i, potion in potion_rows:
        exact(potion, {"name", "present", "potency", "target_kind", "potion_id"})
        if not boolean(potion["present"]):
            continue
        definition = next((r for r in CONTRACT["potions"] if r["name"] == potion["name"]), None)
        if definition is None or potion["potion_id"] != definition["id"]:
            raise ValueError("药水名称/ID未登记")
        refs[(route_zone, i)] = add("POTION", onehot(potion["name"], potion_names) +
                                  [1.0, number(potion["potency"], 20)] + onehot(potion["target_kind"], ["NO_TARGET", "ENEMY"]) +
                                  onehot(lifecycle, CONTRACT["potion_regions"]))
    relic_names = [r["name"] for r in CONTRACT["relics"]]
    seen_relics = set()
    for relic in obs["relics"]:
        if relic["name"] in seen_relics:
            raise ValueError("Duplicate relic instance")
        seen_relics.add(relic["name"])
        if relic_encoder is not None:
            refs[("relic", relic["name"])] = add("RELIC", relic_encoder(relic))
            continue
        exact(relic, {"name", "relic_id", "counter"})
        definition = next((r for r in CONTRACT["relics"] if r["name"] == relic["name"]), None)
        if definition is None or definition["id"] != relic["relic_id"]:
            raise ValueError("遗物名称/ID不一致")
        add("RELIC", onehot(relic["name"], relic_names) + [float(relic["counter"] is not None), number(relic["counter"] or 0, 10)])
    decision = obs["decision"]
    phase = decision.get("phase")
    selection = decision.get("selection")
    if phase == "NORMAL":
        exact(decision, {"phase", "selection"})
        if selection is not None:
            raise ValueError("NORMAL不能携带选牌状态")
        if obs["resolving"] or obs.get("offers") or obs.get("resolving_potions"):
            raise ValueError("NORMAL不能携带尚未结算的来源或offer")
        selection_kind, lo, hi = "NONE", 0, 0
    elif phase == "SELECT_CARD":
        exact(decision, {"phase", "selection", "routing", "resolution_context"})
        exact(decision["routing"], {"decision_id"} | ({"source_ref"} & set(decision["routing"])))
        exact(selection, {"phase", "selection_kind", "candidate_zone", "min_choices", "max_choices", "candidates", "candidate_mask"})
        if selection["phase"] != phase or normal_mask.any():
            raise ValueError("选择阶段不能开放普通动作")
        selection_kind, lo, hi = selection["selection_kind"], selection["min_choices"], selection["max_choices"]
        candidate_context = tuple(resolution_context_features(decision["resolution_context"]))
        if lo != 1 or hi != 1:
            raise ValueError("多选与确认尚未接入")
    else:
        raise ValueError("未知决策阶段")
    player = obs["player"]
    exact(player, set(PLAYER_NUMERIC) | {"statuses"})
    player_features = [number(player[k], scale) for k, scale in PLAYER_NUMERIC.items()]
    player_features += status_features(player["statuses"], CONTRACT["player_statuses"])
    player_features += [number(obs["potion_capacity"], 3)] + onehot(phase, ["NORMAL", "SELECT_CARD"])
    player_features += onehot(selection_kind, CONTRACT["selection_kinds"]) + [number(lo, 10), number(hi, 10)]
    player_ref = add("PLAYER_GLOBAL", player_features)
    if len(tokens) > CONTRACT["resources"]["max_entities"]:
        raise ValueError("总实体超出资源边界；不能丢弃实体")
    if sum(bool(c.get("known_top", False)) for c in obs["draw_pile"]) > 1:
        raise ValueError("只能有一张已知顶牌")
    # 保留零宽关系容器供路由置换兼容；任何伤害预览均不进入tensor。
    edges = np.zeros((len(tokens), len(tokens), 0), dtype=np.float32)
    candidates, routes = [], []

    def candidate(kind, source, target, legal, route, context=DEFAULT_CANDIDATE_CONTEXT):
        candidates.append(Candidate(kind, source, target, bool(legal), tuple(context)))
        routes.append(copy.deepcopy(route))

    if phase == "NORMAL":
        for i, card in enumerate(obs["hand"]):
            if card["target_kind"] == "ENEMY":
                for j in range(5):
                    if ("enemy", j) in refs:
                        candidate("PLAY_TARGET", refs[("hand", i)], refs[("enemy", j)], normal_mask[i * 5 + j], i * 5 + j)
            else:
                candidate("PLAY_SELF", refs[("hand", i)], -1, normal_mask[i * 5], i * 5)
        candidate("END_TURN", player_ref, -1, normal_mask[50], 50)
        for i, potion in enumerate(obs["potions"]):
            if ("potion", i) not in refs:
                continue
            if potion["target_kind"] == "ENEMY":
                for j in range(5):
                    if ("enemy", j) in refs:
                        candidate("POTION_TARGET", refs[("potion", i)], refs[("enemy", j)], normal_mask[51 + i * 5 + j], 51 + i * 5 + j)
            else:
                candidate("POTION_SELF", refs[("potion", i)], -1, normal_mask[51 + i * 5], 51 + i * 5)
        if {r for r, c in zip(routes, candidates) if c.legal} != set(np.flatnonzero(normal_mask)):
            raise ValueError("环境合法动作存在未映射实体或目标")
    else:
        zone = selection["candidate_zone"]
        if zone not in REGIONS:
            raise ValueError("未知候选区域")
        rows = obs.get("offers", []) if zone == "offer" else obs[zone]
        positions = {}
        for i, row in enumerate(rows):
            positions.setdefault(_canonical(row), []).append(refs[(zone, i)])
        mask = np.asarray(selection["candidate_mask"])
        if mask.dtype != np.bool_ or mask.shape != (len(selection["candidates"]),):
            raise ValueError("候选mask不匹配")
        if not mask.any():
            raise ValueError("真实选择阶段必须有合法候选")
        origin = refs.get(("resolving", 0), -1)
        if "source_ref" in decision["routing"]:
            source_ref = decision["routing"]["source_ref"]
            exact(source_ref, {"region", "index"})
            if type(source_ref["index"]) is not int or (source_ref["region"], source_ref["index"]) not in refs:
                raise ValueError("选择来源没有对应公开实体")
            origin = refs[(source_ref["region"], source_ref["index"])]
        for i, row in enumerate(selection["candidates"]):
            matches = positions.get(_canonical(row), [])
            if not matches:
                raise ValueError("候选没有对应的公开实体")
            source = matches.pop(0)
            candidate("SELECT_CARD", source, origin, mask[i],
                      {"kind": "SELECT_CARD", "decision_id": decision["routing"]["decision_id"], "candidate_index": i},
                      candidate_context)
    routing = obs["routing"]
    exact(routing, {"enemy_refs", "stasis_refs", "snapshot"} | ({"bound_card_refs"} & set(routing)))
    if len(routing["enemy_refs"]) != 5 or len(routing["stasis_refs"]) != len(obs["stasis"]):
        raise ValueError("关系路由长度错误")
    enemy_refs = {r: refs[("enemy", i)] for i,r in enumerate(routing["enemy_refs"]) if r is not None and ("enemy",i) in refs}
    card_refs = {r: refs[("stasis", i)] for i,r in enumerate(routing["stasis_refs"])}
    if len(enemy_refs) != sum(e["present"] for e in obs["enemies"]) or len(card_refs) != len(obs["stasis"]):
        raise ValueError("实体引用重复或缺失")
    held = np.full(len(tokens), -1, dtype=np.int64)
    used_cards=set()
    for rel in obs["relations"]:
        if rel.get("kind") == "bottled_card":
            exact(rel, {"kind", "relic_name", "card_ref"})
            location = routing.get("bound_card_refs", {}).get(rel["card_ref"])
            if not isinstance(location, dict): raise ValueError("Missing bottled card endpoint")
            exact(location, {"region", "index"})
            source = refs.get(("relic", rel["relic_name"]))
            target = refs.get((location["region"], _integer(location["index"], "bound index")))
            if source is None or target is None or tokens[target].entity_type != "CARD" or held[source] != -1:
                raise ValueError("Invalid or duplicate bottled relation")
            held[source] = target
            continue
        exact(rel, {"kind", "enemy_ref", "card_ref"})
        if rel["kind"] != "holds_card" or rel["enemy_ref"] not in enemy_refs or rel["card_ref"] not in card_refs:
            raise ValueError("关系端点无效")
        e,c=enemy_refs[rel["enemy_ref"]],card_refs[rel["card_ref"]]
        if held[e] != -1 or c in used_cards: raise ValueError("持牌关系冲突")
        held[e]=c;used_cards.add(c)
    if len(used_cards)!=len(card_refs): raise ValueError("扣牌实体没有持有关系")
    routes=[{"kind":"NORMAL", "snapshot":routing["snapshot"], "action":int(r)} if isinstance(r,(int,np.integer)) else r for r in routes]
    return EntitySample(tokens, edges, candidates, routes, held)


def collate(samples, *, heads=4, resources=None, allow_empty_candidates=False, feature_dims=None):
    """只按本批实际最大长度补齐，资源越界整批拒绝，路由信息不进入tensor。"""
    dimensions = FEATURE_DIMS if feature_dims is None else feature_dims
    limits = CONTRACT["resources"] if resources is None else resources
    if not samples:
        raise ValueError("不能编码空批次")
    b, n, a = len(samples), max(len(s.tokens) for s in samples), max(len(s.candidates) for s in samples)
    if allow_empty_candidates:
        a = max(1, a)
    if n < 1 or a < 1 or n > limits["max_entities"] or a > limits["max_candidates"] or b * heads * n * n > limits["max_attention_elements"]:
        raise ValueError("统一实体批次超出资源边界；必须拆分或重设资源契约，不能丢弃实体")
    batch = {"types": torch.zeros(b, n, dtype=torch.long), "entity_valid": torch.zeros(b, n, dtype=torch.bool),
             "features": {t: torch.zeros(b, n, dim) for t, dim in dimensions.items()},
             "held_card_index": torch.full((b,n), -1, dtype=torch.long), "edges": torch.zeros(b, n, n, 0), "kinds": torch.zeros(b, a, dtype=torch.long),
             "source": torch.full((b, a), -1, dtype=torch.long), "target": torch.full((b, a), -1, dtype=torch.long),
             "candidate_context": torch.zeros(b, a, CANDIDATE_CONTEXT_DIM),
             "candidate_valid": torch.zeros(b, a, dtype=torch.bool), "legal": torch.zeros(b, a, dtype=torch.bool)}
    for i, sample in enumerate(samples):
        length = len(sample.tokens)
        if sample.edges.shape != (length, length, 0) or not np.isfinite(sample.edges).all() or len(sample.routes) != len(sample.candidates):
            raise ValueError("实体关系或路由长度错误")
        held=sample.held_card_index
        if held is None or held.shape!=(length,) or held.dtype.kind not in "iu": raise ValueError("缺少关系路由")
        for source,target in enumerate(held):
            if target != -1 and (not 0<=target<length or sample.tokens[source].entity_type not in {"ENEMY", "RELIC"} or sample.tokens[target].entity_type!="CARD"):
                raise ValueError("关系源/目标类型错误")
        batch["held_card_index"][i,:length]=torch.from_numpy(held.copy())
        for j, token in enumerate(sample.tokens):
            if token.entity_type not in TYPES or token.features.shape != (dimensions[token.entity_type],) or not np.isfinite(token.features).all():
                raise ValueError("实体类型或语义向量错误")
            batch["types"][i, j] = TYPES.index(token.entity_type)
            batch["features"][token.entity_type][i, j] = torch.from_numpy(token.features)
        batch["entity_valid"][i, :length] = True
        batch["edges"][i, :length, :length] = torch.from_numpy(sample.edges)
        for j, c in enumerate(sample.candidates):
            if (c.kind not in KINDS or type(c.source) is not int or type(c.target) is not int or
                    not -1 <= c.source < length or not -1 <= c.target < length or not isinstance(c.legal, bool)):
                raise ValueError("候选类型/引用/合法性错误")
            if (len(c.context) != CANDIDATE_CONTEXT_DIM or
                    not np.isfinite(np.asarray(c.context, dtype=np.float32)).all()):
                raise ValueError("候选公开结算上下文布局或数值错误")
            expected_source = {"PLAY_TARGET": "CARD", "PLAY_SELF": "CARD", "END_TURN": "PLAYER_GLOBAL",
                               "POTION_TARGET": "POTION", "POTION_SELF": "POTION", "SELECT_CARD": "CARD"}[c.kind]
            if c.source < 0 or sample.tokens[c.source].entity_type != expected_source:
                raise ValueError("候选源实体类型不匹配")
            if c.kind.endswith("TARGET") and (c.target < 0 or sample.tokens[c.target].entity_type != "ENEMY"):
                raise ValueError("候选目标必须为敌人实体")
            if (c.kind.endswith("SELF") or c.kind == "END_TURN") and c.target != -1:
                raise ValueError("无目标动作不能携带目标引用")
            if c.kind == "SELECT_CARD" and c.target >= 0 and sample.tokens[c.target].entity_type not in {"CARD", "POTION"}:
                raise ValueError("当前选择来源只支持公开卡牌或药水")
            batch["kinds"][i, j], batch["source"][i, j], batch["target"][i, j] = KINDS.index(c.kind), c.source, c.target
            batch["candidate_context"][i, j] = torch.tensor(c.context, dtype=torch.float32)
            batch["candidate_valid"][i, j], batch["legal"][i, j] = True, c.legal
    return batch


def collate_chunks(samples, *, heads=4):
    """按实际注意力资源拆批；单样本超限仍明确拒绝。"""
    pending = []
    for sample in samples:
        candidate = pending + [sample]
        n = max(len(s.tokens) for s in candidate)
        if pending and len(candidate) * heads * n * n > CONTRACT["resources"]["max_attention_elements"]:
            yield collate(pending, heads=heads)
            pending = []
        pending.append(sample)
    if pending:
        yield collate(pending, heads=heads)
