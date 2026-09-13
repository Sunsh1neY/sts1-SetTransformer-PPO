"""统一实体模型的无活动环境更新边界恢复；拒绝旧模型与契约漂移。"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import tempfile

import numpy as np
import torch

from sts.env.entities import CONTRACT_HASH, FEATURE_DIMS
from sts.env.lightspeed import _load_backend
from sts.models.entities import UnifiedEntityActorCritic

ROOT = Path(__file__).parents[2]
FORMAT = "unified-entity-checkpoint-v1"
BOUNDARY = "no_active_environment_update_boundary"


def fingerprint():
    paths = ["sts/models/unified-entity-contract.json", "sts/env/ironclad-expansion-contract.json",
             "sts/env/ironclad-registry.json", "sts/env/unified-entity-capacity.json", "eval_seeds.json",
             "sts/env/entities.py", "sts/models/entities.py", "sts/env/ironclad.py",
             "sts/env/selection.py", "sts/env/entitycollection.py", "sts/train/entitycheckpoint.py",
             "sts/env/public_battle.py", "sts/env/ironclad_collection.py", "sts/env/lightspeed.py",
             "sts/rewards.py", "sts/train/ppo.py"]
    return {"files": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
            "backend_sha256": hashlib.sha256(Path(_load_backend().__file__).read_bytes()).hexdigest(),
            "entity_contract_sha256": CONTRACT_HASH, "feature_dimensions": FEATURE_DIMS,
            "torch": str(torch.__version__), "numpy": str(np.__version__), "python": list(sys.version_info[:2]),
            "numerical_runtime": {"threads": torch.get_num_threads(), "interop_threads": torch.get_num_interop_threads(),
                                  "default_dtype": str(torch.get_default_dtype()),
                                  "deterministic": torch.are_deterministic_algorithms_enabled(),
                                  "matmul_tf32": torch.backends.cuda.matmul.allow_tf32,
                                  "cudnn_tf32": torch.backends.cudnn.allow_tf32,
                                  "cudnn_deterministic": torch.backends.cudnn.deterministic,
                                  "cudnn_benchmark": torch.backends.cudnn.benchmark}}


def save_entity_checkpoint(path, model, optimizer=None, *, update_index=0, boundary=BOUNDARY):
    if type(model) is not UnifiedEntityActorCritic or boundary != BOUNDARY:
        raise ValueError("只支持统一实体模型的无活动环境更新边界")
    if type(update_index) is not int or update_index < 0:
        raise ValueError("更新计数必须为非负整数")
    if torch.get_default_dtype() != torch.float32 or any(p.dtype != torch.float32 for p in model.parameters()):
        raise ValueError("首版精确恢复只支持默认FP32，不包含混合精度或GradScaler")
    if optimizer is not None:
        if type(optimizer) is not torch.optim.Adam or len(optimizer.param_groups) != 1:
            raise ValueError("首版恢复只支持单参数组Adam")
        if [id(p) for p in optimizer.param_groups[0]["params"]] != [id(p) for p in model.parameters()]:
            raise ValueError("优化器参数与模型顺序不一致")
    path = Path(path)
    if path.exists():
        raise FileExistsError("检查点已存在，请使用新的更新编号")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"format": FORMAT, "boundary": boundary, "fingerprint": fingerprint(),
               "architecture": model.configuration(), "model_state": model.state_dict(),
               "optimizer_state": None if optimizer is None else optimizer.state_dict(),
               "update_index": update_index, "device": str(next(model.parameters()).device),
               "torch_rng": torch.get_rng_state(),
               "cuda_rng": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else []}
    # 先写同目录临时文件再替换，避免半份checkpoint被读取。
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name, suffix=".tmp", delete=False) as handle:
        temporary = Path(handle.name)
    try:
        torch.save(payload, temporary)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def load_entity_checkpoint(path, *, device="cpu", restore_rng=True):
    try:
        payload = torch.load(path, map_location=device, weights_only=True)
    except Exception as error:
        raise ValueError("无法读取为受支持的统一实体checkpoint") from error
    if not isinstance(payload, dict) or payload.get("format") != FORMAT or payload.get("boundary") != BOUNDARY:
        raise ValueError("旧MLP/卡牌Set或其他边界不能作为统一实体精确恢复")
    if payload["fingerprint"] != fingerprint():
        raise ValueError("checkpoint的代码、输入、内容、资源或后端契约不匹配")
    if payload["device"] != str(torch.device(device)):
        raise ValueError("跨设备只能另行迁移，不能声称精确恢复")
    if len(payload["cuda_rng"]) != (torch.cuda.device_count() if torch.cuda.is_available() else 0):
        raise ValueError("CUDA设备集合与恢复契约不一致")
    model = UnifiedEntityActorCritic(payload["architecture"]).to(device)
    if any(t.dtype != torch.float32 for t in payload["model_state"].values()):
        raise ValueError("模型权重精度不匹配，不允许隐式转换")
    model.load_state_dict(payload["model_state"], strict=True)
    optimizer = None
    if payload["optimizer_state"] is not None:
        optimizer = torch.optim.Adam(model.parameters())
        optimizer.load_state_dict(payload["optimizer_state"])
    if restore_rng:
        torch.set_rng_state(payload["torch_rng"].cpu())
        if payload["cuda_rng"]:
            torch.cuda.set_rng_state_all([state.cpu() for state in payload["cuda_rng"]])
    return model, optimizer, {"update_index": payload["update_index"], "boundary": BOUNDARY,
                              "rng_restored": restore_rng, "fingerprint": payload["fingerprint"]}
