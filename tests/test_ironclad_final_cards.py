"""动态卡、差异修复、自动打出及生成闭包。"""
import pytest
from test_ironclad_dynamics import start,play,rows
from test_ironclad_direct import upgraded
from test_ironclad_selection_cards import choose
from sts.env.entities import encode_observation


@pytest.mark.parametrize('up',[False,True])
def test_anger_generates_one_matching_upgrade(up):
    env,obs=start([upgraded('Anger',up),*['Strike_R']*4]);obs=play(env,obs,'Anger')
    assert len(rows(obs,'Anger'))==2
    assert all(c['upgrade_count']==int(up) for c in rows(obs,'Anger'))


@pytest.mark.parametrize('up',[False,True])
def test_perfected_strike_counts_strike_cards_including_self(up):
    env,obs=start([upgraded('Perfected Strike',up),'Strike_R','Twin Strike','Pommel Strike','Defend_R'])
    before=obs['enemies'][0]['hp']+obs['enemies'][0]['block'];obs=play(env,obs,'Perfected Strike')
    assert before-obs['enemies'][0]['hp']-obs['enemies'][0]['block']==6+4*(3 if up else 2)


@pytest.mark.parametrize('level',[0,1,2,5,100])
def test_searing_blow_multilevel_reset_and_damage(level):
    env,obs=start(['Searing Blow'+(f'+{level}' if level else ''),*['Strike_R']*4])
    card=next(c for c in obs['hand'] if c['name']=='Searing Blow')
    assert card['upgrade_count']==level and card['damage']==12+level*(level+7)//2
    encode_observation(obs)


def test_searing_blow_bound_rejects_instead_of_wrapping():
    with pytest.raises((ValueError,RuntimeError)):
        start(['Searing Blow+101',*['Strike_R']*4])


@pytest.mark.parametrize('up',[False,True])
def test_whirlwind_uses_environment_energy_for_all_enemy_hits(up):
    env,obs=start([upgraded('Whirlwind',up),*['Strike_R']*4]);before=obs['enemies'][0]['hp']+obs['enemies'][0]['block']
    obs=play(env,obs,'Whirlwind')
    assert obs['player']['energy']==0
    assert before-obs['enemies'][0]['hp']-obs['enemies'][0]['block']==3*(8 if up else 5)


@pytest.mark.parametrize('up',[False,True])
def test_disarm_upgrade_strength_reduction(up):
    env,obs=start([upgraded('Disarm',up),*['Strike_R']*4]);obs=play(env,obs,'Disarm')
    assert obs['enemies'][0]['statuses']['Strength']==(-3 if up else -2)


@pytest.mark.parametrize('up',[False,True])
def test_iron_wave_dexterity_applies_once(up):
    env,obs=start([upgraded('Iron Wave',up),*['Strike_R']*4],['Dexterity Potion',None])
    obs=env.step(51)[0];obs=play(env,obs,'Iron Wave')
    assert obs['player']['block']==(7 if up else 5)+2


@pytest.mark.parametrize('up',[False,True])
def test_fiend_fire_hits_original_hand_and_exhausts_source(up):
    env,obs=start([upgraded('Fiend Fire',up),'Sentinel','Wound','Strike_R','Defend_R'], ['Explosive Potion', None])
    before=obs['enemies'][0]['hp']+obs['enemies'][0]['block'];obs=play(env,obs,'Fiend Fire')
    assert before-obs['enemies'][0]['hp']-obs['enemies'][0]['block']==4*(10 if up else 7)
    assert len(obs['exhaust_pile'])==5


@pytest.mark.parametrize('up',[False,True])
def test_double_tap_repeats_attack_and_consumes_charge(up):
    env,obs=start([upgraded('Double Tap',up),'Strike_R','Strike_R','Defend_R','Defend_R'])
    obs=play(env,obs,'Double Tap');before=obs['enemies'][0]['hp']+obs['enemies'][0]['block'];obs=play(env,obs,'Strike_R')
    assert before-obs['enemies'][0]['hp']-obs['enemies'][0]['block']==12
    assert obs['player']['statuses'].get('Double Tap',0)==int(up)


@pytest.mark.parametrize('up',[False,True])
def test_havoc_autoplay_can_pause_for_true_grit_choice(up):
    env,obs=start([upgraded('Havoc',up),'Warcry','True Grit+1','Sentinel','Wound'])
    obs=play(env,obs,'Warcry');obs=choose(env,obs,'True Grit')
    obs=play(env,obs,'Havoc')
    assert obs['decision']['phase']=='SELECT_CARD'
    obs=choose(env,obs,'Sentinel')
    assert {'True Grit','Sentinel','Warcry'} <= {c['name'] for c in obs['exhaust_pile']}


@pytest.mark.parametrize('up',[False,True])
def test_infernal_blade_generated_attack_cost_is_temporary(up):
    env,obs=start([upgraded('Infernal Blade',up),*['Defend_R']*4]);obs=play(env,obs,'Infernal Blade')
    generated=next(c for c in obs['hand'] if c['card_type']=='ATTACK')
    if generated['cost_kind']=='ENERGY':assert generated['effective_cost']==0
    assert any(c['name']=='Infernal Blade' for c in obs['exhaust_pile'])
    encode_observation(obs)


def test_fiend_fire_dark_embrace_exhausts_snapshot_not_new_draws():
    from test_ironclad_expansion import scene
    from sts.env.ironclad import IroncladEnv
    candidate=scene(['Dark Embrace+1','Fiend Fire','Sentinel','Wound','Dazed','Burn','Slimed','Strike_R','Defend_R'])
    candidate.update(encounter='LAGAVULIN',relics=[])
    env=IroncladEnv()
    for seed in range(985100,985200):
        obs=env.reset(candidate,seed,diagnostic=True)
        if {'Dark Embrace','Fiend Fire'} <= {c['name'] for c in obs['hand']}:break
    obs=play(env,obs,'Dark Embrace');original={c['name'] for c in obs['hand']}
    obs=play(env,obs,'Fiend Fire')
    assert {c['name'] for c in obs['exhaust_pile']}==original
    # 原三张手牌和Fiend Fire来源自身共耗尽四张，各触发一次抽牌。
    assert len(obs['hand'])==4


def test_combust_can_continue_when_all_other_cards_exhausted():
    env,obs=start(['Combust','Fiend Fire','Sentinel','Wound','Dazed'])
    obs=play(env,obs,'Combust');obs=play(env,obs,'Fiend Fire')
    assert not obs['hand'] and not obs['draw_pile'] and not obs['discard_pile']
    assert obs['action_mask'][50]
    obs,_,terminated,_,_=env.step(50)
    assert not terminated


def test_infernal_actual_pool_is_fully_reachable_without_filtering():
    import json,re
    from pathlib import Path
    from sts.env.ironclad import IroncladEnv
    from test_ironclad_expansion import scene
    root=Path(__file__).resolve().parents[1]
    source=(root/'third_party/sts_lightspeed/include/constants/CardPools.h').read_text(encoding='utf-8')
    pool=re.findall(r'CardId::(\w+)',source.split('namespace CombatTypeCardPool {')[1].split('};')[0])
    ledger=json.loads((root/'sts/env/ironclad-expansion-coverage.json').read_text(encoding='utf-8'))['versions']
    mapping={r['backend_enum']:r['name'] for r in ledger}
    expected={mapping[name] for name in pool};assert len(expected)==28
    candidate=scene(['Infernal Blade']+['Defend_R']*4);candidate.update(encounter='LAGAVULIN',relics=[])
    env=IroncladEnv();seen=set()
    for seed in range(985500,986000):
        obs=env.reset(candidate,seed,diagnostic=True);obs=play(env,obs,'Infernal Blade')
        seen.update(c['name'] for c in obs['hand'] if c['card_type']=='ATTACK')
        encode_observation(obs)
        if seen==expected:break
    assert seen==expected


def test_limit_break_large_values_raise_resource_error_before_overflow():
    from sts.env.ironclad import IroncladEnv
    from test_ironclad_expansion import scene
    candidate=scene(['Limit Break+1','Limit Break+1','Flex','Defend_R','Defend_R'])
    candidate.update(encounter='LAGAVULIN',relics=[]);candidate['player'].update(hp=32767,max_hp=32767)
    env=IroncladEnv();obs=env.reset(candidate,986100,diagnostic=True)
    with pytest.raises(RuntimeError,match='力量'):
        for _ in range(150):
            name='Flex' if obs['player']['statuses'].get('Strength',0)==0 else 'Limit Break'
            slot=next((i for i,c in enumerate(obs['hand']) if c['name']==name and obs['action_mask'][i*5]),None)
            obs=env.step(slot*5 if slot is not None else 50)[0]


@pytest.mark.parametrize('up',[False,True])
def test_double_tap_rampage_second_hit_uses_instance_growth(up):
    env,obs=start(['Double Tap',upgraded('Rampage',up),*['Defend_R']*3])
    obs=play(env,obs,'Double Tap');before=obs['enemies'][0]['hp']+obs['enemies'][0]['block']
    obs=play(env,obs,'Rampage')
    assert before-obs['enemies'][0]['hp']-obs['enemies'][0]['block']==16+(8 if up else 5)
    assert rows(obs,'Rampage')[0]['combat_damage_bonus']==2*(8 if up else 5)


def test_armaments_upgrades_searing_blow_multiple_times():
    env,obs=start(['Searing Blow+2','Armaments','Armaments','Strike_R','Strike_R'])
    for _ in range(2):
        obs=play(env,obs,'Armaments');obs=choose(env,obs,'Searing Blow')
    assert rows(obs,'Searing Blow')[0]['upgrade_count']==4


def test_dual_wield_keeps_rampage_growth_in_copies():
    env,obs=start(['Rampage','Dual Wield','Defend_R','Strike_R','Strike_R'])
    obs=play(env,obs,'Rampage');obs=env.step(50)[0]
    obs=play(env,obs,'Dual Wield');obs=choose(env,obs,'Rampage')
    assert [c['combat_damage_bonus'] for c in rows(obs,'Rampage')]==[5,5]


def test_juggernaut_metallicize_can_continue_without_cards():
    env,obs=start(['Juggernaut','Metallicize','Fiend Fire','Sentinel','Wound'],['Energy Potion',None])
    obs=env.step(51)[0];obs=play(env,obs,'Juggernaut');obs=play(env,obs,'Metallicize');obs=play(env,obs,'Fiend Fire')
    assert not obs['hand'] and obs['action_mask'][50]
    before=obs['enemies'][0]['hp']+obs['enemies'][0]['block'];obs,_,terminated,_,_=env.step(50)
    assert not terminated
    assert obs['enemies'][0]['hp']+obs['enemies'][0]['block']<before


def test_remaining_potion_prevents_no_card_automatic_loss():
    env,obs=start(['Fiend Fire','Sentinel','Wound','Dazed','Burn'],['Explosive Potion',None])
    obs=play(env,obs,'Fiend Fire')
    assert not obs['hand'] and obs['action_mask'][51]
