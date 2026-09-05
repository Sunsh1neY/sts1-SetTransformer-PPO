// lightspeed-probe —— 差分对拍的高吞吐真值探针（不修改锁定源码，仅链接其产物）
//
// 用法1（battle-init）: lightspeed_probe <seed> <mapCol>
//   进首层第 col 列首个房间，若是战斗则打印完整 BattleContext（与 ConsoleSimulator
//   printActions 同构，Python 侧 parse_last_bc 可直接复用）；否则打印 NO_BATTLE。
// 用法2（逐步模式，预留）: lightspeed_probe <seed> <mapCol> <动作文件>
//
// 编译（MSYS2 mingw64，D15 摩擦三件套）:
//   g++ -O2 -I third_party/sts_lightspeed/include -I third_party/sts_lightspeed/json/include
//       scripts/lightspeed-probe.cpp <src 全部 .cpp 除 SaveFile> -o build/lightspeed_probe.exe
//       -include algorithm -include numeric -include cstdint
#include <iostream>
#include <fstream>
#include <string>

#include "game/GameContext.h"
#include "combat/BattleContext.h"

int main(int argc, char **argv) {
    if (argc < 3) {
        std::cerr << "usage: lightspeed_probe <seed> <mapCol> [actionFile]\n";
        return 2;
    }
    const std::uint64_t seed = std::stoull(argv[1]);
    const int col = std::stoi(argv[2]);

    sts::GameContext gc(sts::CharacterClass::IRONCLAD, seed, 0);
    gc.chooseEventOption(1);      // Neow：奖励随 seed 变化，由 Python 侧按快照过滤
    gc.transitionToMapNode(col);  // 首个 MONSTER 房（首行各列的 y=0 节点）

    if (gc.screenState != sts::ScreenState::BATTLE) {
        std::cout << "NO_BATTLE\n";
        return 0;
    }

    sts::BattleContext bc;
    bc.init(gc);
    std::cout << bc << '\n';
    return 0;
}
