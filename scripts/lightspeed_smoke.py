"""lightspeed ConsoleSimulator 冒烟：验证「子进程 stdin 管道」驱动命令流的可行性。

这是第 3 周差分对拍通道（U6 双轨之一）的入口实验：
- pybind 模块 slaythespire 的 play() = ConsoleSimulator.play(std::cin, std::cout, ctx)，
  从真实 stdin 逐行读命令；用 python -c 启动子进程即可注入命令流，零源码改动。
- 首行协议：`<seedStr> <character> <ascension>`；print all 打印整个 GameContext。

用法：python scripts/lightspeed_smoke.py [seed]
"""
import subprocess
import sys
import os

BUILD_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "third_party", "sts_lightspeed", "build"))

BOOT = (
    "import sys; sys.path.insert(0, r'" + BUILD_DIR + "'); "
    "import slaythespire; slaythespire.play()"
)


def run_commands(commands: str, timeout: int = 60) -> tuple[str, str, int]:
    """把命令流喂给 slaythespire.play() 子进程，返回 (stdout, stderr, returncode)。"""
    p = subprocess.run(
        [sys.executable, "-c", BOOT],
        input=commands.encode(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    return p.stdout.decode(errors="replace"), p.stderr.decode(errors="replace"), p.returncode


if __name__ == "__main__":
    seed = sys.argv[1] if len(sys.argv) > 1 else "42"
    commands = f"{seed} IRONCLAD 0\nprint all\n"
    out, err, rc = run_commands(commands)
    print("=== STDOUT ===")
    print(out[:4000])
    print("=== STDERR ===")
    print(err[:1500])
    print("=== rc =", rc)
