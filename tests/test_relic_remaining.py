"""Mechanism checks for I13 remaining combat imports."""
import pytest
from test_relic_batch_two import start, status
from test_relic_state import play


def test_abacus_shuffle_block_and_no_opening_trigger():
    env, o, _ = start(['The Abacus'], deck=['Defend_R'] * 5)
    assert o['player']['block'] == 0
    o = env.step(50)[0]
    assert o['player']['block'] == 6
    o = env.step(50)[0]
    assert o['player']['block'] == 6


def test_akabeko_consumed_only_by_first_attack_and_reset():
    env, o, s = start(['Akabeko'], deck=['Strike_R'] * 10)
    assert status(o['player'], 'Vigor') == 8
    before = o['enemies'][0]['hp']
    o = play(env, o, 'Strike_R')[0]
    assert before - o['enemies'][0]['hp'] == 14
    assert status(o['player'], 'Vigor') == 0
    before = o['enemies'][0]['hp']
    o = play(env, o, 'Strike_R')[0]
    assert before - o['enemies'][0]['hp'] == 6
    assert status(env.reset(s, 100124, diagnostic=True)['player'], 'Vigor') == 8


@pytest.mark.parametrize('card,damage', [('Strike_R',9), ('Anger',6), ('Pommel Strike',12)])
def test_strike_dummy_tags(card, damage):
    env, o, _ = start(['Strike Dummy'], deck=[card] * 10)
    before = o['enemies'][0]['hp']
    o = play(env, o, card)[0]
    assert before - o['enemies'][0]['hp'] == damage


@pytest.mark.parametrize('relic,blocks', [('Horn Cleat',[0,14,0,0]), ("Captain\'s Wheel",[0,0,18,0])])
def test_once_at_exact_turn(relic, blocks):
    env, o, _ = start([relic], encounter='LAGAVULIN', deck=['Defend_R']*10)
    for expected in blocks:
        assert o['player']['block'] == expected
        o = env.step(50)[0]


def test_brimstone_both_sides_each_turn():
    env, o, _ = start(['Brimstone'], encounter='LAGAVULIN')
    for turn in range(1,4):
        assert status(o['player'],'Strength') == 2*turn
        assert status(o['enemies'][0],'Strength') == turn
        o = env.step(50)[0]


@pytest.mark.parametrize('encounter,expected', [('JAW_WORM',0),('GREMLIN_NOB',2),('THE_GUARDIAN',0),('COLOSSEUM_EVENT_NOBS',0)])
def test_sling_elite_trigger(encounter,expected):
    _, o, _ = start(['Sling of Courage'],encounter=encounter)
    assert status(o['player'],'Strength') == expected


def test_mercury_opening_and_next_turn():
    env, o, _ = start(['Mercury Hourglass'],encounter='THREE_SENTRIES')
    _, b, _ = start(encounter='THREE_SENTRIES')
    for m,n in zip(o['enemies'],b['enemies']):
        if m['present']: assert n['hp']-m['hp']==3
    hp=[m['hp'] for m in o['enemies']]
    o=env.step(50)[0]
    for h,m in zip(hp,o['enemies']):
        if m['present']: assert h-m['hp']==3


def test_thread_armor_starts_once_and_decays_on_unblocked_hit():
    env,o,_=start(['Thread and Needle'],encounter='THREE_SENTRIES')
    assert status(o['player'],'Plated Armor')==4
    o=env.step(50)[0]
    assert 0 < status(o['player'],'Plated Armor') < 4


@pytest.mark.parametrize('encounter,hp,expected',[('JAW_WORM',40,40),('THE_GUARDIAN',40,65),('COLLECTOR',70,80)])
def test_pantograph_boss_heal_cap(encounter,hp,expected):
    _,o,_=start(['Pantograph'],encounter=encounter,hp=hp)
    assert o['player']['hp']==expected


@pytest.mark.parametrize('relic',['Busted Crown','Coffee Dripper','Cursed Key','Fusion Hammer',"Philosopher's Stone",'Mark of Pain'])
def test_energy_relics_every_turn_and_start_effect(relic):
    env,o,_=start([relic],encounter='LAGAVULIN',deck=['Defend_R']*10)
    assert o['player']['energy']==4
    if relic=="Philosopher's Stone": assert status(o['enemies'][0],'Strength')==1
    cards=o['hand']+o['draw_pile']
    assert sum(c['name']=='Wound' for c in cards)==(2 if relic=='Mark of Pain' else 0)
    o=env.step(50)[0]
    assert o['player']['energy']==4


def test_boot_each_small_attack_hit():
    env,o,_=start(['The Boot'],deck=['Pummel']*10)
    before=o['enemies'][0]['hp']
    o=play(env,o,'Pummel')[0]
    assert before-o['enemies'][0]['hp']==20


def test_paper_phrog_vulnerable_multiplier():
    env,o,_=start(['Paper Phrog','Bag of Marbles'])
    before=o['enemies'][0]['hp']
    o=play(env,o)[0]
    assert before-o['enemies'][0]['hp']==10


def test_calipers_loses_fifteen_instead_of_all_block():
    env,o,_=start(['Calipers'],encounter='LAGAVULIN',deck=['Impervious']*10)
    o=play(env,o,'Impervious')[0]
    assert o['player']['block']==30
    o=env.step(50)[0]
    assert o['player']['block']==15
    o=env.step(50)[0]
    assert o['player']['block']==0


def test_ice_cream_carries_only_unspent_energy():
    env,o,_=start(['Ice Cream'],encounter='LAGAVULIN',deck=['Defend_R']*10)
    o=play(env,o,'Defend_R')[0]
    assert o['player']['energy']==2
    o=env.step(50)[0]
    assert o['player']['energy']==5


def test_bird_urn_power_only_heal_cap():
    env,o,_=start(['Bird-Faced Urn'],hp=79,deck=['Inflame']*10)
    o=play(env,o,'Inflame')[0]
    assert o['player']['hp']==80
    env,o,_=start(['Bird-Faced Urn'],hp=70)
    o=play(env,o)[0]
    assert o['player']['hp']==70


def test_charon_exhaust_hits_all():
    env,o,_=start(["Charon's Ashes"],encounter='THREE_SENTRIES',deck=['Seeing Red']*10)
    before=[m['hp'] for m in o['enemies']]
    o=play(env,o,'Seeing Red')[0]
    assert all(h-m['hp']==3 for h,m in zip(before,o['enemies']) if m['present'])


def test_chemical_x_whirlwind_adds_two_hits():
    env,o,_=start(['Chemical X'],deck=['Whirlwind']*10)
    hp=o['enemies'][0]['hp']
    o=play(env,o,'Whirlwind')[0]
    assert hp-o['enemies'][0]['hp']==25
    assert o['player']['energy']==0


@pytest.mark.parametrize('relic,loss',[('Tungsten Rod',2),('Torii',3),('Fossilized Helix',0)])
def test_hp_loss_damage_type_and_buffer(relic,loss):
    env,o,_=start([relic],deck=['Bloodletting']*10)
    o=play(env,o,'Bloodletting')[0]
    assert o['player']['hp']==70-loss
    if relic=='Fossilized Helix': assert status(o['player'],'Buffer')==0


def test_art_of_war_current_attack_count_controls_next_turn():
    env,o,_=start(['Art of War'],encounter='LAGAVULIN')
    assert o['player']['energy']==3
    o=env.step(50)[0]
    assert o['player']['energy']==4
    o=play(env,o)[0]
    o=env.step(50)[0]
    assert o['player']['energy']==3


@pytest.mark.parametrize('relic,power',[('Kunai','Dexterity'),('Shuriken','Strength'),('Ornamental Fan',None)])
def test_third_attack_and_turn_reset(relic,power):
    env,o,_=start([relic],encounter='THE_GUARDIAN',deck=['Anger']*20)
    for i in range(3): o=play(env,o,'Anger')[0]
    assert (status(o['player'],power) if power else o['player']['block'])==(1 if power else 4)
    o=env.step(50)[0]
    o=play(env,o,'Anger')[0]
    assert (status(o['player'],power) if power else o['player']['block'])==(1 if power else 0)


def test_letter_opener_third_skill_aoe():
    env,o,_=start(['Letter Opener'],encounter='THREE_SENTRIES',deck=['Flex']*10)
    hp=[m['hp'] for m in o['enemies']]
    for i in range(3): o=play(env,o,'Flex')[0]
    assert all(h-m['hp']==5 for h,m in zip(hp,o['enemies']) if m['present'])


def test_self_forming_clay_public_next_turn_block():
    env,o,_=start(['Self-Forming Clay'],encounter='LAGAVULIN',deck=['Bloodletting']*10)
    o=play(env,o,'Bloodletting')[0]
    assert status(o['player'],'Next Turn Block')==3
    o=env.step(50)[0]
    assert o['player']['block']==3
    assert status(o['player'],'Next Turn Block')==0


def test_runic_cube_draw_per_hp_loss_event():
    env,o,_=start(['Runic Cube'],deck=['Bloodletting']*15)
    for i in range(2):
        before=len(o['draw_pile'])
        o=play(env,o,'Bloodletting')[0]
        assert len(o['hand'])==5 and len(o['draw_pile'])==before-1


def test_red_skull_entry_threshold_and_crossing():
    _,o,_=start(['Red Skull'],hp=40)
    assert status(o['player'],'Strength')==3
    env,o,_=start(['Red Skull'],hp=41,deck=['Bloodletting']*10)
    assert status(o['player'],'Strength')==0
    o=play(env,o,'Bloodletting')[0]
    assert status(o['player'],'Strength')==3


@pytest.mark.parametrize('plays,expected',[(0,8),(3,8),(4,5)])
def test_pocketwatch_prior_turn_threshold(plays,expected):
    env,o,_=start(['Pocketwatch'],encounter='LAGAVULIN',deck=['Flex']*20)
    assert len(o['hand'])==5
    for i in range(plays): o=play(env,o,'Flex')[0]
    o=env.step(50)[0]
    assert len(o['hand'])==expected


def test_gremlin_horn_nonfinal_kill_draw_energy():
    env,o,_=start(['Gremlin Horn'],encounter='THREE_SENTRIES',deck=['Searing Blow+10']*15)
    o=play(env,o,'Searing Blow')[0]
    assert o['player']['energy']==2 and len(o['hand'])==5


def test_magic_flower_combat_heal_rounding():
    _,o,_=start(['Magic Flower','Blood Vial'],hp=60)
    assert o['player']['hp']==63


def test_gremlin_visage_weak_and_ginger_immunity():
    _,o,_=start(['Gremlin Visage'])
    assert status(o['player'],'Weak')==1
    _,o,_=start(['Gremlin Visage','Ginger'])
    assert status(o['player'],'Weak')==0


def test_champion_belt_vulnerable_adds_weak():
    env,o,_=start(["Champion's Belt"],deck=['Bash']*10)
    o=play(env,o,'Bash')[0]
    assert status(o['enemies'][0],'Weak')==1
    assert status(o['enemies'][0],'Vulnerable')==2


def test_mummified_hand_zeroes_eligible_card():
    env,o,_=start(['Mummified Hand'],deck=['Inflame']*10)
    o=play(env,o,'Inflame')[0]
    assert sum(c['effective_cost']==0 for c in o['hand'])==1


def test_warped_tongs_one_upgrade_per_turn():
    env,o,_=start(['Warped Tongs'],encounter='LAGAVULIN',deck=['Defend_R']*20)
    assert sum(c['upgrade_count'] for c in o['hand'])==1
    o=env.step(50)[0]
    assert sum(c['upgrade_count'] for c in o['hand'])==1


@pytest.mark.parametrize('relic',['Sozu','Ectoplasm'])
def test_restrictive_energy_relics(relic):
    env,o,_=start([relic],encounter='LAGAVULIN')
    assert o['player']['energy']==4
    assert env.step(50)[0]['player']['energy']==4


def test_face_of_cleric_victory_max_hp():
    env,o,_=start(['Face of Cleric'],deck=['Searing Blow+10']*10)
    o,r,term,_,_=play(env,o,'Searing Blow')
    assert term and o['player']['max_hp']==81 and o['player']['hp']==71


@pytest.mark.parametrize('n',range(4))
def test_girya_exact_supplied_lifts(n):
    _,o,_=start([dict(name='Girya',counter=n)])
    assert status(o['player'],'Strength')==n


@pytest.mark.parametrize('n',range(4))
def test_neow_entry_consumption_and_exit_no_double_decrement(n):
    env,o,_=start([dict(name="Neow's Lament",counter=n)],deck=['Searing Blow+10']*10)
    relic=o['relics'][0]
    assert relic['state']['counter']['value']==max(0,n-1)
    assert (o['enemies'][0]['hp']==1)==(n>0)
    o,_,term,_,info=play(env,o,'Searing Blow')
    assert term
    assert info['battle_exit']['relics'][0]['counter']==max(0,n-1)


@pytest.mark.parametrize('n',[0,1])
def test_tea_set_explicit_ready_consumed_once(n):
    env,o,_=start([dict(name='Ancient Tea Set',counter=n)],encounter='LAGAVULIN')
    assert o['player']['energy']==3+2*n
    assert o['relics'][0]['state']['counter']['value']==0
    assert env.step(50)[0]['player']['energy']==3


def test_centennial_puzzle_public_consumption():
    env,o,_=start(['Centennial Puzzle'],deck=['Bloodletting']*20)
    assert o['relics'][0]['state']['counter']['value']==0
    o=play(env,o,'Bloodletting')[0]
    assert o['relics'][0]['state']['counter']['value']==1
    assert len(o['hand'])==7
    o=play(env,o,'Bloodletting')[0]
    assert len(o['hand'])==6


def test_du_vu_master_deck_curse_count():
    _,o,_=start(['Du-Vu Doll'],deck=['AscendersBane']*2+['Strike_R']*10)
    assert status(o['player'],'Strength')==2


from sts.env.relic_state import REGISTRY, relic_features
from sts.models.apath import encode, APathActorCritic, batch_samples
import torch
import json
from pathlib import Path
RUN_OWNERSHIP=json.loads(Path('docs/relic-remaining-execution.json').read_text(encoding='utf-8'))['run_ownership']


@pytest.mark.parametrize('name',list(RUN_OWNERSHIP))
def test_run_ownership_preserves_configured_state_and_terminal(name):
    initial=dict(name=name,counter=0) if name in ('Omamori','Maw Bank') else name
    env,o,_=start([initial],hp=61,max_hp=87,deck=['Searing Blow+10']*10)
    assert o['player']['hp']==61 and o['player']['max_hp']==87
    assert len(o['hand'])+len(o['draw_pile'])==10
    assert o['relics'][0]['name']==name
    assert sum(relic_features(o['relics'][0])[:len(REGISTRY['identity_columns'])])==1
    sample=encode(o)
    assert any(t.entity_type=='RELIC' for t in sample.entities.tokens)
    o,_,term,trunc,info=play(env,o,'Searing Blow')
    assert term and not trunc
    assert o['player']['hp']==61 and o['player']['max_hp']==87


def test_maw_bank_active_entry_and_bloody_idol():
    _,o,_=start([dict(name='Maw Bank',counter=1),'Bloody Idol'],hp=60)
    assert o['player']['hp']==65
    _,o,_=start([dict(name='Maw Bank',counter=0),'Bloody Idol'],hp=60)
    assert o['player']['hp']==60


@pytest.mark.parametrize('relics,loss',[([],5),(['Torii'],1),(['Torii','Tungsten Rod'],0)])
def test_torii_attack_threshold_before_tungsten(relics,loss):
    env,o,_=start(relics,encounter='THREE_SENTRIES',deck=['Defend_R']*10)
    o=play(env,o,'Defend_R')[0]
    o=env.step(50)[0]
    assert 70-o['player']['hp']==loss


def test_hand_drill_breaks_block():
    env,o,_=start(['Hand Drill','Strike Dummy'],encounter='LAGAVULIN')
    assert o['enemies'][0]['block']==8
    o=play(env,o)[0]
    assert status(o['enemies'][0],'Vulnerable')==2


@pytest.mark.parametrize('relics,loss',[([],15),(['Odd Mushroom'],12)])
def test_odd_mushroom_player_vulnerable(relics,loss):
    env,o,_=start(relics,encounter='THREE_SENTRIES',deck=['Berserk']*10)
    o=play(env,o,'Berserk')[0]
    o=env.step(50)[0]
    assert 70-o['player']['hp']==loss


def test_toy_ornithopter_use_not_discard_and_heal_cap():
    from sts.env.relics import RelicEnv
    s=__import__('test_relic_state').scene(['Toy Ornithopter'])
    s['potions']=['Block Potion',None]
    env=RelicEnv();o=env.reset(s,100123,diagnostic=True)
    o,_,_,_,_=env.step(51)
    assert o['player']['hp']==75 and not o['potions'][0]['present']


def test_stone_calendar_seventh_end_turn():
    env,o,_=start(['Stone Calendar'],encounter='THE_GUARDIAN',hp=500,max_hp=500,deck=['Defend_R']*20)
    for turn in range(1,8):
        hp=o['enemies'][0]['hp'];block=o['enemies'][0]['block']
        o=env.step(50)[0]
        if turn<7: assert o['enemies'][0]['hp']==hp
        else: assert hp-o['enemies'][0]['hp']==max(0,52-block)


def test_turnip_prevents_frail_from_shelled_parasite():
    env,o,_=start(['Turnip'],encounter='SHELL_PARASITE',hp=500,max_hp=500,deck=['Defend_R']*20)
    baseline,b,_=start(encounter='SHELL_PARASITE',hp=500,max_hp=500,deck=['Defend_R']*20)
    seen=False
    for i in range(5):
        o=env.step(50)[0];b=baseline.step(50)[0]
        assert status(o['player'],'Frail')==0
        seen |= status(b['player'],'Frail')>0
    assert seen


from test_relic_batch_two import ACT12
NEW_RELICS=REGISTRY['relics'][33:]


def remaining_initial(row):
    rule=row['counter']
    return dict(name=row['name'],counter=rule['max']) if rule and 'reset_on_battle_start' not in rule else row['name']


@pytest.mark.parametrize('row',NEW_RELICS,ids=lambda r:r['name'])
def test_remaining_model_forward_and_deterministic_replay(row):
    from sts.env.relics import RelicEnv
    from sts.train.apath import sample_digest
    env,o,s=start([remaining_initial(row)],deck=['Strike_R','Defend_R','Inflame']+['Defend_R']*12)
    model=APathActorCritic().eval()
    with torch.no_grad():
        dist,value=model(batch_samples([encode(o)]))
    assert value.isfinite().all() and dist.probs.sum().item()==pytest.approx(1)
    other=RelicEnv();other.reset(json.loads(json.dumps(s)),100123,diagnostic=True)
    after=env.step(50);replay=other.step(50)
    assert sample_digest(encode(after[0]))==sample_digest(encode(replay[0]))
    assert after[1:4]==replay[1:4]
    assert not after[4]['training_admitted']


@pytest.mark.parametrize('encounter',ACT12)
@pytest.mark.parametrize('row',NEW_RELICS,ids=lambda r:r['name'])
def test_remaining_act12_reset_step_surface(row,encounter):
    env,o,_=start([remaining_initial(row)],encounter=encounter,deck=['Defend_R']*20)
    assert encode(o).routes
    o=env.step(50)[0]
    assert encode(o).entities.tokens


def test_ectoplasm_blocks_maw_bank_gold_and_idol_heal():
    _,o,_=start(['Ectoplasm',dict(name='Maw Bank',counter=1),'Bloody Idol'],hp=60)
    assert o['player']['hp']==60


def test_sozu_does_not_disable_owned_potion():
    from sts.env.relics import RelicEnv
    s=__import__('test_relic_state').scene(['Sozu']);s['potions']=['Block Potion',None]
    env=RelicEnv();env.reset(s,100123,diagnostic=True)
    o=env.step(51)[0]
    assert not o['potions'][0]['present'] and o['player']['block']==12


def test_gremlin_visage_clockwork_artifact_order():
    for relics in [['Gremlin Visage','Clockwork Souvenir'],['Clockwork Souvenir','Gremlin Visage']]:
        _,o,_=start(relics)
        assert status(o['player'],'Weak')==0
        assert status(o['player'],'Artifact')==0


def test_red_skull_healing_above_threshold_removes_strength():
    from sts.env.relics import RelicEnv
    s=__import__('test_relic_state').scene(['Red Skull','Toy Ornithopter']);s['player']['hp']=40;s['potions']=['Block Potion',None]
    env=RelicEnv();o=env.reset(s,100123,diagnostic=True)
    assert status(o['player'],'Strength')==3
    o=env.step(51)[0]
    assert o['player']['hp']>40 and status(o['player'],'Strength')==0


def test_magic_flower_rounds_odd_heal_up():
    from sts.env.relics import RelicEnv
    s=__import__('test_relic_state').scene(['Magic Flower','Toy Ornithopter']);s['player']['hp']=60;s['potions']=['Block Potion',None]
    env=RelicEnv();env.reset(s,100123,diagnostic=True)
    assert env.step(51)[0]['player']['hp']==68


@pytest.mark.parametrize('name',['Girya',"Neow's Lament",'Ancient Tea Set','Omamori','Maw Bank'])
@pytest.mark.parametrize('value',[None,-1,True,1.5,100])
def test_required_initial_counter_rejects_missing_or_invalid(name,value):
    from sts.env.relic_state import validate_initial_relics
    with pytest.raises((ValueError,TypeError)):
        validate_initial_relics([dict(name=name,counter=value)])
    with pytest.raises((ValueError,TypeError)):
        validate_initial_relics([name])


def test_centennial_continuation_state_cannot_be_injected_as_battle_start():
    from sts.env.relic_state import validate_initial_relics
    with pytest.raises(ValueError):
        validate_initial_relics([dict(name='Centennial Puzzle',counter=1)])


def test_gremlin_visage_weak_expires_after_first_player_turn():
    env,o,_=start(['Gremlin Visage'],encounter='LAGAVULIN')
    assert status(o['player'],'Weak')==1
    o=env.step(50)[0]
    assert status(o['player'],'Weak')==0
