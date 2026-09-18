"""Build a scope/state audit from local reference metadata, without copying code."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / 'reference/relic-act12-audit/decompiled/com/megacrit/cardcrawl'
JAR = Path('E:/SteamLibrary/steamapps/common/SlayTheSpire/desktop-1.0.jar')
ALIASES = dict(Boot='THE_BOOT', CultistMask='CULTIST_HEADPIECE', FrozenEgg2='FROZEN_EGG',
    GremlinMask='GREMLIN_VISAGE', MoltenEgg2='MOLTEN_EGG', NlothsMask='NLOTHS_HUNGRY_FACE',
    PaperCrane='PAPER_KRANE', PaperFrog='PAPER_PHROG', Sling='SLING_OF_COURAGE', ToxicEgg2='TOXIC_EGG')
BATCH_TWO = {'BagOfMarbles', 'RedMask', 'ClockworkSouvenir', 'PreservedInsect',
             'SlaversCollar', 'BlackBlood', 'MeatOnTheBone', 'Orichalcum'}
EVENTS = {
    'CultistMask': 'Face Trader; Acts 1/2', 'GremlinMask': 'Face Trader; Acts 1/2',
    'FaceOfCleric': 'Face Trader; Acts 1/2', 'NlothsMask': 'Face Trader; Acts 1/2',
    'SsserpentHead': 'Face Trader; Acts 1/2', 'NeowsLament': 'Neow; run start',
    'GoldenIdol': 'Golden Idol; Act 1', 'OddMushroom': 'Mushrooms; Act 1',
    'WarpedTongs': 'Accursed Blacksmith; shared special event',
    'SpiritPoop': 'Bonfire Spirits; shared special event',
    'BloodyIdol': 'Forgotten Altar; Act 2, requires Golden Idol exchange',
    'MutagenicStrength': 'Augmenter / Drug Dealer; Act 2',
    'RedMask': 'Masked Bandits; Act 2 (also later-act acquisition outside this scope)',
    'Enchiridion': 'Cursed Tome; Act 2', 'Necronomicon': 'Cursed Tome; Act 2',
    'NilrysCodex': 'Cursed Tome; Act 2', "NlothsGift": "N'loth; Act 2, requires relic exchange",
    'MarkOfTheBloom': 'Mind Bloom; Act 3 only in the standard finite run',
}
# State requirements are semantic audit conclusions, not copied implementations.
STATES = {
    'AncientTeaSet': 'Rest-room carry-in eligibility and first-turn consumption; require explicit entry context.',
    'ArtOfWar': 'Whether an attack was played last/current turn and first-turn state.',
    'BottledFlame': 'Exact bound attack-card instance; persisted master-deck relation.',
    'BottledLightning': 'Exact bound skill-card instance; persisted master-deck relation.',
    'BottledTornado': 'Exact bound power-card instance; persisted master-deck relation.',
    'CentennialPuzzle': 'First HP-loss trigger used_this_combat; queued draw timing.',
    'DuVuDoll': 'Master-deck curse count, distinct from transient combat cards.',
    'FossilizedHelix': 'Remaining buffer is public player status; entry application must occur once.',
    'GamblingChip': 'Opening trigger consumed plus explicit discard selection and continuation.',
    'Girya': 'Persistent rest-site lift count (0..3); cannot infer it from ownership.',
    'HappyFlower': 'Public persistent turn counter; initialization advances the first turn.',
    'IncenseBurner': 'Public persistent turn counter plus player Intangible status.',
    'InkBottle': 'Public persistent card-play counter; distinguish plays/replays from manual actions.',
    'Kunai': 'Attack progress within this turn; shared attack history only if event semantics match.',
    'LetterOpener': 'Skill progress within this turn; reset at the proper turn boundary.',
    'LizardTail': 'Persistent spent/remaining-use state; lethal interception and resurrection order.',
    'Matryoshka': 'Persistent remaining chest uses; relevant to run state, not a new battle counter.',
    'MawBank': 'Persistent spent state after spending gold; entry/run transition provenance.',
    'Necronomicon': 'Used_this_turn, replay eligibility and curse/deck effect; replay source context.',
    'NeowsLament': 'Remaining protected combats and entry consumption; persistent state required.',
    'NilrysCodex': 'Explicit end-turn offer, optional selection, generation and continuation.',
    'NlothsMask': 'Persistent next-chest suppression consumed/spent state.',
    'Nunchaku': 'Public persistent attack counter; energy gain uses actual engine events.',
    'Omamori': 'Persistent remaining curse-prevention charges.',
    'OrangePellets': 'Attack/skill/power event-type bit vector for this turn; actual debuff removal.',
    'OrnamentalFan': 'Attack progress within this turn; shared history must match event semantics.',
    'PenNib': 'Public persistent attack progress and public double-damage status; map internal sentinel.',
    'Pocketwatch': 'Previous-turn card count and first-turn state, not just current-turn statistics.',
    'RedSkull': 'HP-threshold active state and applied Strength; avoid double application on restore.',
    'Shuriken': 'Attack progress within this turn; shared history must match event semantics.',
    'StoneCalendar': 'Combat turn/trigger progress; verify seventh-turn scheduling.',
    'Sundial': 'Public persistent shuffle progress, not turn count.',
    'TinyChest': 'Persistent unknown-room progress; run state only.',
    'UnceasingTop': 'Draw enabled/temporarily disabled state plus pending draw/selection queue.',
    'VelvetChoker': 'Actual cards played this turn, including automatic plays; action legality.',
    'WingBoots': 'Persistent remaining path bypass charges; run state only.',
    'Orichalcum': 'Current public block at end-turn; reference trigger latch has no nondefault writer in the inspected JAR.',
    'PreservedInsect': 'Encounter elite-trigger classification and original/current monster HP.',
    'SlaversCollar': 'Encounter elite-trigger or boss-enemy classification; energy reset across battles.',
    'MeatOnTheBone': 'HP/max HP at pre-victory-healing point; threshold before victory relic callbacks.',
    'BlackBlood': 'Victory/current HP; replaces Burning Blood, reject simultaneous ownership.',
}
SPECIAL = {
    'BottledFlame': 'card-instance binding', 'BottledLightning': 'card-instance binding',
    'BottledTornado': 'card-instance binding', 'GamblingChip': 'new selection flow',
    'NilrysCodex': 'selection/generation', 'Toolbox': 'selection/colorless generation',
    'FrozenEye': 'draw-order visibility', 'RunicDome': 'enemy-intent visibility',
    'PotionBelt': 'potion/action capacity', 'PrismaticShard': 'card/orb scope',
    'DeadBranch': 'generated-card closure', 'Enchiridion': 'generated power pool',
    'Necronomicon': 'automatic replay and curse semantics', 'LizardTail': 'resurrection/termination',
    'SacredBark': 'all potion potency and automatic-use branches',
    'StrangeSpoon': 'exhaust replacement and randomness',
    'UnceasingTop': 'draw/action-queue closure', 'SneckoEye': 'cost randomness and visibility',
    'RunicPyramid': 'retention/hand-capacity interactions', 'VelvetChoker': 'card-play legality',
    'BlueCandle': 'curse play legality and HP loss', 'MedicalKit': 'status play legality',
    'MutagenicStrength': 'acquisition-order interaction with Artifact',
    'OrangePellets': 'multi-event state and removal scope',
}
RUN_ONLY = set('Astrolabe BlackStar CallingBell Cauldron CeramicFish Courier DarkstonePeriapt DollysMirror DreamCatcher EmptyCage EternalFeather FrozenEgg2 GoldenIdol JuzuBracelet Mango Matryoshka MawBank MealTicket MembershipCard MoltenEgg2 NlothsGift NlothsMask OldCoin Omamori Orrery PandorasBox PeacePipe Pear PrayerWheel QuestionCard RegalPillow Shovel SingingBowl SmilingMask SpiritPoop SsserpentHead Strawberry TinyChest TinyHouse ToxicEgg2 Waffle WarPaint Whetstone WhiteBeast WingBoots CultistMask'.split())


def main():
    lib = (REF / 'helpers/RelicLibrary.java').read_text(encoding='utf-8')
    pools = {cls: pool or 'Shared' for pool, cls in re.findall(r'RelicLibrary.add(Red|Green|Blue|Purple)?\(new (\w+)\(\)\)', lib)}
    upstream = json.loads((ROOT/'docs/evidence/relic-audit-ledger-first-batch.json').read_bytes())['relics']
    norm = lambda name: re.sub('[^a-z0-9]', '', name.lower())
    lookup = {norm(r[k]): r for r in upstream for k in ('upstream_enum', 'upstream_name')}
    by_enum = {r['upstream_enum']: r for r in upstream}
    rows = []
    for path in sorted((REF/'relics').rglob('*.java')):
        cls = path.stem
        if cls == 'AbstractRelic':
            continue
        s = path.read_text(encoding='utf-8')
        rid = re.search(r'String ID = "([^"]+)"', s)
        tier = re.search(r'RelicTier\.(\w+)', s)
        original_id = rid.group(1) if rid else None
        old = by_enum.get(ALIASES.get(cls)) or lookup.get(norm(cls)) or lookup.get(norm(original_id or ''))
        pool = pools.get(cls)
        hooks = re.findall(r'public (?:[\w<>\[\].]+) (\w+)\(', s)
        hooks = [m for m in hooks if m not in {'getUpdatedDescription','makeCopy','update','render','renderInTopPanel','renderTip','updateDescription','setDescriptionAfterLoading'}]
        fields = re.findall(r'^    (?:private|public|protected) (?!static)(?:[\w<>\[\].]+) (\w+)[ =;]', s, re.M)
        tier = tier.group(1) if tier else None
        if pool in {'Green', 'Blue', 'Purple'}:
            scope, acquisition = 'other_character', 'Outside standard Ironclad acquisition; custom/Daily modes require separate admission.'
        elif cls == 'MarkOfTheBloom':
            scope, acquisition = 'act3_only', EVENTS[cls]
        elif cls in {'Circlet', 'RedCirclet'}:
            scope, acquisition = 'fallback_or_special_mode', 'Not in normal RelicLibrary pools; fallback/endless provenance must be reviewed.'
        elif pool is None:
            scope, acquisition = 'unregistered_or_deprecated', 'Class is present but not registered by RelicLibrary.initialize; do not treat as obtainable.'
        else:
            scope = 'act12_candidate'
            acquisition = EVENTS.get(cls) or {
                'STARTER': 'Ironclad starting relic; can be replaced by Neow or Black Blood.',
                'BOSS': 'Act 1 boss chest for Act 2 carry-in; Neow only where its rules permit; Act 2 chest is after its final battle.',
                'SHOP': 'Shop pool, subject to canSpawn and unlock conditions.',
            }.get(tier, 'Shared/Ironclad tier pool via eligible rewards, chests, events or shops; subject to canSpawn/unlock conditions.')
        spawn = []
        if 'boolean canSpawn()' in s:
            body = s.split('boolean canSpawn()',1)[1].split('\n    }',1)[0]
            if 'floorNum' in body:
                limits = sorted(set(re.findall(r'floorNum\s*(?:<=|>=|<|>)\s*(\d+)',body)))
                spawn.append('Floor-dependent eligibility; inspected threshold(s): '+', '.join(limits)+'. Relevant late-floor exclusions do not remove early Act 1/2 carry-in.')
            if 'ShopRoom' in body: spawn.append('Cannot spawn from the inspected shop-room path.')
            if 'hasRelic' in body: spawn.append('Requires the corresponding starter relic; replacement ownership must be enforced.')
            if 'actNum' in body: spawn.append('New acquisition restricted to Act 1; ownership may carry into Act 2.')
            if 'CardHelper' in body or 'masterDeck' in body: spawn.append('Requires eligible cards/types in the master deck.')
            if 'campfireRelicCount' in body: spawn.append('Limited by existing campfire-option relics.')
            if not spawn: spawn.append('Additional canSpawn condition requires targeted review.')
        imported = bool(old and old['implementation_status']=='diagnostic_tested')
        state = STATES.get(cls)
        if not state:
            if cls in RUN_ONLY:
                state = 'Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation.'
            elif fields:
                state = 'Inspect semantic role/visibility of reference instance fields: '+', '.join(fields)+'. Do not export implementation flags blindly.'
            else:
                state = 'Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import.'
        if scope != 'act12_candidate':
            disposition = 'excluded_or_conditional'
        elif cls in SPECIAL:
            disposition = 'owner_review_required'
        elif imported:
            disposition = 'first_batch_diagnostic'
        elif cls in BATCH_TWO:
            disposition = 'second_batch_candidate'
        elif cls in RUN_ONLY:
            disposition = 'run_or_acquisition_effect'
        else:
            disposition = 'later_combat_batch'
        rows.append(dict(original_class=cls, original_id=original_id, tier=tier,
            pool=pool, scope=scope, acquisition=acquisition, spawn_constraints=spawn,
            upstream_enum=old['upstream_enum'] if old else None,
            backend_references=old['source_occurrences'] if old else [],
            reference_hooks=hooks, reference_instance_fields=fields,
            required_state_assessment=state, disposition=disposition,
            special_review=SPECIAL.get(cls),
            adapter_status='diagnostic_imported_before_this_audit' if imported else 'not_imported_at_audit_baseline',
            behavior_status='scoped_simulator_tests_only' if imported else 'not_runtime_certified',
            reference=dict(jar_class='com/megacrit/cardcrawl/relics/'+path.relative_to(REF/'relics').with_suffix('.class').as_posix(),
                           local_metadata_sha256=hashlib.sha256(path.read_bytes()).hexdigest()),
            confidence='high_for_catalog_and_hook_presence; proposed_state_requires_per_mechanism_validation',
            verified_on='2026-09-19'))
    mapped = {r['upstream_enum'] for r in rows if r['upstream_enum']}
    assert len(pools)==178
    assert {r['upstream_enum'] for r in upstream} <= mapped
    assert sum(r['pool'] is not None for r in rows)==178
    counts = {key:dict(Counter(r[key] for r in rows)) for key in ('scope','disposition')}
    result = dict(schema='act12-relic-scope-audit-v1', date='2026-09-19',
        baseline='9d95526', mode='standard finite Ironclad; all unlocks as potential catalog',
        jar_sha256=hashlib.sha256(JAR.read_bytes()).hexdigest(),
        upstream_commit='7476a81954020087da31d41d16fddf475746ec2d',
        evidence_boundary='Complete class/pool/state-risk static audit, not all-relic runtime equivalence. Original code remains ignored and is not part of this artifact.',
        counts=counts, relics=rows)
    out=ROOT/'docs/evidence/act12-relic-scope-audit.json'
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    lines=['# Act 1/2 relic audit matrix','',
        'Baseline: `9d95526`. Standard finite Ironclad; potential catalog assumes relevant unlocks. Full structured evidence and source locations: [audit JSON](evidence/act12-relic-scope-audit.json).',
        '', 'This is a complete static inventory and risk review, not a declaration that all mechanisms pass runtime tests. Unregistered/deprecated and other-character entries are retained with explicit scope.', '',
        '| Original class / ID | Tier / pool | Scope | Disposition | Required state / review |',
        '|---|---|---|---|---|']
    for r in rows:
        cells=[r['original_class']+' / '+str(r['original_id']),str(r['tier'])+' / '+str(r['pool']),r['scope'],r['disposition'],r['required_state_assessment']+(' Owner review: '+r['special_review'] if r['special_review'] else '')]
        lines.append('| '+' | '.join(c.replace('|','/') for c in cells)+' |')
    (ROOT/'docs/act12-relic-audit-matrix.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(counts,indent=2))


if __name__=='__main__':
    main()
