# 桌面 STS 仓库清理与恢复说明

2026-09-14 用户授权自主清理桌面的 STS 辅助仓库，并将重要内容集中保存到主项目。此授权替代先前保留桌面辅助工作树的布局要求；历史代码、实验和检查点仍完整保留。

## 清理结果

- 桌面仅保留 `C:\Users\19091\Desktop\sts2` 作为 STS 主目录；其他无关项目未处理。
- 主仓库仅登记 `main` 一个工作树和本地分支。其他 14 个本地分支已先保存到 Git bundle，再删除本地分支名称。
- 未合入 main 的 A 路径及其他历史提交保留在 bundle，未因清理而自动合并。
- 主后端、json 和 pybind11 的 origin 已恢复到相应 GitHub 上游；当前主后端对象库独立，不再需要桌面的 act12 仓库提供下载地址。
- 自动审批检查拦截批量删除后，改为将 6 个原目录完整移入归档区。原目录与 ZIP 双份保留；本轮整理桌面，不以释放磁盘空间为目标。

## 归档位置

主归档：`C:\Users\19091\Desktop\sts2\reference\desktop-repo-archive-20260914`。

| 文件或目录 | 内容 |
|---|---|
| `all-refs.bundle` | 清理前所有 Git 引用及其可达提交历史，已通过 bundle verify |
| `manifest.json` | 原路径、分支提交、工作树状态及每个文件的 SHA-256 |
| `original-directories/` | 6 个原目录的完整内容，含未提交和忽略文件 |
| 六份同名 `.zip` | 原目录逐文件校验通过的压缩副本 |
| `cleanup-verification.json` | 搬迁后的文件校验及 main 实际后端验证 |
| `main-cpu-regression.log`、`main-cpp-regression.log` | 清理后回归日志 |

六个原目录为 `sts-worktree-consolidation`、`sts2-act12-main`、`sts2-integration`、`sts2-enemy-baseline-backend`、`sts2-enemy-baseline-build`、`sts2-enemy-patch-repro`。共 6,194 个文件，ZIP 内容与搬迁后的原文件均核对 SHA-256。

A 路径训练结果位于归档原目录 `sts2-integration/runs/a-path-ppo-20260914-v1`，对应的源码、契约及旧后端也一并保留。基线后端未提交的修改包含在其原目录和 ZIP 中。

归档位于被忽略的 `reference/`，不会随普通 Git push 上传。备份主项目时须连同这个目录一起复制。

## 恢复方法与边界

在主项目中可从 bundle 恢复任意已保存分支，例如：

```powershell
git fetch ./reference/desktop-repo-archive-20260914/all-refs.bundle refs/heads/codex/a-path-agent:refs/heads/codex/a-path-agent
```

恢复文件时可直接从 ZIP 或 `original-directories` 复制；不要覆盖正在使用的 main。原目录作为文件快照保留，旧的工作树 `.git` 指针已不再有效，不能直接当作已登记的 Git 工作树使用。需要继续开发时，从 bundle 恢复分支后新建工作树，再按清单恢复未跟踪产物，不覆盖新工作树的顶层 `.git`。

旧构建缓存含历史绝对路径，搬迁后不能宣称可直接续训或增量编译。恢复训练前须验证对应旧契约和检查点，并重建所需后端。主项目旧 `.git/modules` 对象存储仍保留，归档中的部分旧依赖元数据曾借用它；不能只凭移动目录就假定旧依赖仓库已独立。

## 主环境验证

清理过程未修改 main 的模拟器、模型、奖励、种子或训练范围。清理前后后端 SHA-256 均为 `2c3256c28c5e3701e2705ec297f07017ce2f36a5230b7da682cdf78f061ea28c`；全卡入口与原采集环境创建成功。

清理后完整 CPU 回归 1,345 项通过（130.51 秒），独立 C++ 夹具 1 项通过（2.48 秒），均无失败或跳过。本轮仅补充清理及恢复文档，没有启动训练或执行 push。
