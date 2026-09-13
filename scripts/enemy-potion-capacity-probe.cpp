// 独立扩展容器满载测试；关闭assert时仍必须在写入前抛错。
#include "combat/ActionQueue.h"
#include "combat/CardQueue.h"
#include <iostream>
int main() {
    for (bool front : {false, true}) {
        sts::ActionQueue<50> actions;
        actions.checkedCapacity = true;
        for (int i=0; i<50; ++i) actions.pushBack(sts::Action([](sts::BattleContext &) {}));
        bool rejected=false;
        try {
            if(front) actions.pushFront(sts::Action([](sts::BattleContext &) {}));
            else actions.pushBack(sts::Action([](sts::BattleContext &) {}));
        } catch(const std::overflow_error &) { rejected=true; }
        if(!rejected || actions.size!=50) return 1;
        sts::CardQueue cards;
        cards.checkedCapacity=true;
        for(int i=0;i<10;++i) cards.pushBack(sts::CardQueueItem{});
        rejected=false;
        try { if(front) cards.pushFront(sts::CardQueueItem{}); else cards.pushBack(sts::CardQueueItem{}); }
        catch(const std::overflow_error &) { rejected=true; }
        if(!rejected || cards.size!=10) return 2;
    }
    std::cout << "4 capacity checks passed\n";
}
