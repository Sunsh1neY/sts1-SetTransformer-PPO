# 全卡扩展独立工作目录

创建日期：2026-09-12。

- 原训练目录：`C:/Users/19091/Desktop/sts2`，分支 `main`。
- 扩展目录：`C:/Users/19091/Desktop/sts2-full-card`，分支 `codex/ironclad-full-expansion`。
- 基础提交：`0d68033d2b2fb7a042d33343b863af7c3e818967`。
- 起始快照包含复制时原目录全部已跟踪文件和未被忽略的新文件，共 200 个；未提交的比较实现作为开发快照保留，不代表正式训练完成或验收通过。审计、需求和扩展计划一并保留。
- 原目录工作文件、暂存区和分支不因快照提交改变；两目录共享 Git 历史，分别提交。不要在一个目录切换到另一个工作目录正在使用的分支。

## 开发入口

```powershell
Set-Location C:\Users\19091\Desktop\sts2-full-card
.\.venv\Scripts\python.exe -m pytest -q tests/test_public_battle.py tests/test_real_deck_batch.py
# 后续确有 C++ 修改时再独立构建；当前初始化没有运行编译。
.\scripts\build-lightspeed.ps1 -Python .\.venv\Scripts\python.exe -Jobs 1
```

新 `.venv` 使用系统只读依赖作为基础（`--system-site-packages`），项目可编辑安装位于新环境，当前 torch 为 `2.6.0+cpu`。这并非完全独立的依赖副本；后续安装应指定新环境的 Python，不要升级系统依赖或原 `.venv-gpu`。当前不启动训练。日志和 checkpoint 使用新目录下相对路径 `runs/full-card-...`；不要把原训练输出目录作为目标。

C++ 源码、其 Git 元数据及子模块已普通复制到新目录，不使用硬链接或目录联接。仅复制当前 `.pyd` 和运行 DLL 以便轻量测试；未复制含旧绝对路径的 CMake 缓存和构建对象。后续构建会使用新目录。`third_party/` 仍被主仓库忽略，后端修改必须按项目现有补丁工作流保存，不能仅依赖主仓库提交。

原训练产物、GPU 环境、原始研究数据及其他被忽略的 reference 文件没有批量复制。后续需要时单独复制必要输入。初始化哈希清单位于本目录被忽略的 `reference/worktree-snapshot.json`。

## 已验证与边界

- 200 个源文件复制前后无变化，原暂存区哈希一致。
- 新 Python、项目模块和后端扩展实际解析路径均位于新工作目录。
- 公开环境及真实卡组回归：22 项通过。
- C++ 新编译、全卡行为、模型训练与正式对照验收均未在此初始化中执行。
- 下一阶段按 `ironclad-full-expansion-plan.md` 推进；当前比较结果尚未正式冻结，复制的实现不是最终比较基线，后续需显式同步和记录。
