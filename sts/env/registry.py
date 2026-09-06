"""卡牌类别注册表：把后端枚举映射为项目稳定 ID 与公开动作语义。"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import IntEnum
from typing import Iterable


SCHEMA_VERSION = 2
REGISTRY_VERSION = 1
PAD_ID = 0


class CardLocation(IntEnum):
    """卡牌公开区域；0 专用于张量 padding。"""

    PAD = 0
    HAND = 1
    DRAW = 2
    DISCARD = 3
    EXHAUST = 4


class TargetKind(IntEnum):
    """卡牌动作的语义目标；与环境动作列号分开。"""

    PAD = 0
    NO_TARGET = 1
    ENEMY = 2


@dataclass(frozen=True)
class CardDefinition:
    """一类卡牌的稳定映射和当前机制所需公开元数据。"""

    registry_id: int
    backend_card_id: int
    name: str
    target_kind: TargetKind


class CardRegistry:
    """拒绝未知类别的只读注册表。"""

    def __init__(
        self,
        definitions: Iterable[CardDefinition],
        *,
        version: int = REGISTRY_VERSION,
    ) -> None:
        entries = tuple(definitions)
        if version <= 0:
            raise ValueError("registry version 必须为正整数")
        if any(entry.registry_id <= PAD_ID for entry in entries):
            raise ValueError("有效 registry_id 必须大于 PAD_ID=0")
        if len({entry.registry_id for entry in entries}) != len(entries):
            raise ValueError("registry_id 不能重复")
        if len({entry.backend_card_id for entry in entries}) != len(entries):
            raise ValueError("backend_card_id 不能重复")
        if len({entry.name for entry in entries}) != len(entries):
            raise ValueError("卡牌名称不能重复")
        self.version = version
        self._entries = entries
        self._by_backend_id = {entry.backend_card_id: entry for entry in entries}
        self._by_registry_id = {entry.registry_id: entry for entry in entries}

    @property
    def entries(self) -> tuple[CardDefinition, ...]:
        return self._entries

    @property
    def content_hash(self) -> str:
        payload = {
            "version": self.version,
            "entries": [
                {
                    **asdict(entry),
                    "target_kind": int(entry.target_kind),
                }
                for entry in sorted(self._entries, key=lambda item: item.registry_id)
            ],
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
        return hashlib.sha256(encoded).hexdigest()

    def from_backend_id(self, backend_card_id: int) -> CardDefinition:
        try:
            return self._by_backend_id[int(backend_card_id)]
        except KeyError as exc:
            raise ValueError(
                f"后端返回未登记的有效 card_id={backend_card_id}"
            ) from exc

    def from_registry_id(self, registry_id: int) -> CardDefinition:
        try:
            return self._by_registry_id[int(registry_id)]
        except KeyError as exc:
            raise ValueError(f"未知 registry_id={registry_id}") from exc


DEFAULT_CARD_REGISTRY = CardRegistry(
    (
        CardDefinition(1, 25, "Bash", TargetKind.ENEMY),
        CardDefinition(2, 104, "Defend", TargetKind.NO_TARGET),
        CardDefinition(3, 321, "Strike", TargetKind.ENEMY),
    )
)
