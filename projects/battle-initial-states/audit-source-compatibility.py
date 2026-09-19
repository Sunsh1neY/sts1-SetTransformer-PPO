"""Audit pinned run metadata, act coverage and source-certification limits offline."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import zipfile
from source_fields import combat_floor

ROOT = Path(__file__).resolve().parents[2]
PROJECT = Path(__file__).resolve().parent
RECORDER_COMMIT = '99ad7fbb462caaa2eb82ed0fc2151dd2bf2fc48b'
RECORDER_HASH = '4272eb2dec27d613f356bfa0f2df21358cef9a00a5fda54de3db76a177425cf3'
MODE_FLAGS = ('is_daily', 'is_endless', 'is_trial', 'is_beta', 'is_prod', 'chose_seed')
MANIFEST_FIELDS = ('mods', 'mod_list', 'mod_ids', 'mod_versions', 'mod_manifest',
                   'game_binary_sha256', 'recorder_version', 'recorder_commit')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def band(floor):
    floor = combat_floor(floor)
    if floor <= 17: return 'act1'
    if floor <= 34: return 'act2'
    if floor <= 51: return 'act3'
    return 'act4_or_later'


def classify(run):
    """Report observed contradictions separately; dates/nulls are not certificates."""
    mismatch = [flag for flag in ('is_daily', 'is_endless', 'is_trial', 'is_beta')
                if run.get(flag) is True]
    if mismatch:
        return {'status': 'declared_mode_outside_pilot', 'reasons': mismatch}
    return {'status': 'unverified', 'reasons': [
        'NO_VERIFIED_RUN_LINKED_GAME_RULES_MANIFEST',
        'NO_VERIFIED_RUN_LINKED_RECORDER_AND_MOD_MANIFEST',
    ]}


def source_name(path):
    parts = Path(path).parts
    if len(parts) < 3 or parts[0] != 'runs':
        raise ValueError('Unexpected pinned source layout')
    return parts[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-root', type=Path, required=True)
    args = parser.parse_args()
    module_path = ROOT/'scripts/audit-public-corpus.py'
    spec = importlib.util.spec_from_file_location('fixed_source_audit', module_path)
    audit = importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)
    archive = args.reference_root/'public-run-corpus/matiger-fixed.zip'
    groups = audit.group_records(audit.load_records(archive.read_bytes()))
    recorder = args.reference_root/'public-run-corpus/run-history-plus-2022.zip'
    if digest(recorder) != RECORDER_HASH:
        raise ValueError('Pinned recorder source archive mismatch')
    evidence = []
    for filename, claim in [
        ('NeowBonusRunHistoryPatch.java', 'Neow choices and result logging hooks exist'),
        ('PotionRunHistoryPatch.java', 'Floor-indexed use/discard/acquisition logs exist; not original slot snapshots'),
        ('ImprovableCardRunHistoryPatch.java', 'Permanent values read from final master deck in gatherAllData'),
        ('GreenKeyTakenRunHistoryPatch.java', 'Records key-claim floor; not every elite enhancement'),
    ]:
        relative = 'src/main/java/runhistoryplus/patches/'+filename
        with zipfile.ZipFile(recorder) as zip_file:
            content = zip_file.read('RunHistoryPlus-'+RECORDER_COMMIT+'/'+relative)
        local = args.reference_root/'public-run-corpus/recorder-2022'/relative
        if content != local.read_bytes():
            raise ValueError('Extracted recorder source differs from pinned ZIP: '+relative)
        evidence.append({'source_id':'RHP-'+filename.removesuffix('.java'),
                         'url':f'https://github.com/modargo/RunHistoryPlus/blob/{RECORDER_COMMIT}/{relative}',
                         'sha256':hashlib.sha256(content).hexdigest(), 'claim':claim,
                         'confidence':'high for source code, not installed historical version',
                         'verified_on':'2026-09-19'})
    with zipfile.ZipFile(archive) as zip_file:
        docs = []
        for name in sorted(zip_file.namelist()):
            if name.lower().endswith('.md'):
                content = zip_file.read(name).decode('utf-8')
                hits = [{'line':i,'text':line} for i,line in enumerate(content.splitlines(),1)
                        if any(term in line.lower() for term in (
                            'modthespire','basemod','mod list','mods','run history plus','version'))]
                if hits: docs.append({'path':name.split('/',1)[1],'hits':hits})

    rows=[]; grouped=defaultdict(list); combat_counts=Counter(); act_groups=Counter()
    final_cards=Counter(); final_lengths=[]; final_unique=set(); entry_example=None
    pilot = [json.loads(line) for line in (PROJECT/'pilot-states.jsonl').read_bytes().splitlines()]
    by_group={g['group_id']:g for g in groups}
    for g in groups:
        run=g['run']; acts=Counter(band(c['floor']) for c in run['damage_taken'])
        combat_counts.update(acts);act_groups.update(acts.keys())
        deck=run.get('master_deck')
        valid_deck=isinstance(deck,list) and bool(deck) and all(isinstance(c,str) and c for c in deck)
        if not valid_deck: raise ValueError('Malformed or missing final master deck: '+g['group_id'])
        final_lengths.append(len(deck)); final_cards.update(c.split('+')[0] for c in deck)
        final_unique.add(tuple(sorted(deck)))
        row={'source_group':g['group_id'],'source':source_name(g['source_path']),
             'raw_path':g['source_path'],'raw_sha256':g['raw_sha256'],'aliases':g['aliases'],
             'build_version':run['build_version'],
             'timestamp_utc':datetime.fromtimestamp(run['timestamp'],timezone.utc).isoformat(),
             'ascension':run['ascension_level'],'mode_flags':{k:run.get(k) for k in MODE_FLAGS},
             'combat_counts_by_floor_band':dict(acts),
             'final_deck':{'size':len(deck),'semantic':'run-end master deck',
                           'hash':hashlib.sha256(json.dumps(sorted(deck)).encode()).hexdigest()},
             'card_modifier_evidence':audit.card_modifier_evidence(run),
             'present_manifest_fields':[k for k in MANIFEST_FIELDS if k in run],
             'metadata_keys':[k for k in sorted(run) if re.search(r'mod|version|build',k)],
             'source_compatibility':classify(run),
             'recorder_match':'field-family match; exact installed recorder not established',
             'training_admitted':False}
        rows.append(row); grouped[(row['source'],row['build_version'])].append(row)
    for state in pilot:
        origin=state['provenance']['origins'][0]
        run=by_group[origin['source_group']]['run']
        if state['state']['floor']==1 and Counter(state['state']['deck']) != Counter(run['master_deck']):
            entry_example={'scene_id':origin['scene_id'],'raw_path':origin['source_path'],
                           'state_hash':state['state_hash'],'entry_floor':1,
                           'entry_deck_size':len(state['state']['deck']),
                           'final_deck_size':len(run['master_deck']),
                           'different_multisets':True}
            break
    matrix=[]
    for (source,build), members in sorted(grouped.items()):
        matrix.append({'source':source,'build_version':build,'groups':len(members),
                       'representative':members[0]['raw_path'],
                       'run_dates_utc':[min(r['timestamp_utc'] for r in members),max(r['timestamp_utc'] for r in members)],
                       'modifiers':dict(Counter(r['card_modifier_evidence'] for r in members)),
                       'compatibility':dict(Counter(r['source_compatibility']['status'] for r in members)),
                       'direct_historical_installation_evidence':False})
    field_names=sorted(set().union(*(g['run'] for g in groups)))
    out={'schema':'small-corpus-source-compatibility-audit-v1','date':'2026-09-19',
         'source_sha256':digest(archive),'source_commit':audit.COMMIT,
         'recorder_commit':RECORDER_COMMIT,'recorder_archive_sha256':digest(recorder),
         'source_evidence':evidence,'repository_metadata_document_hits':docs,
         'counts':{'source_groups':len(groups),'combats':sum(combat_counts.values()),
                   'combat_by_floor_band':dict(combat_counts),'groups_with_combats':dict(act_groups),
                   'final_decks':len(final_lengths),'final_deck_size_min':min(final_lengths),
                   'final_deck_size_max':max(final_lengths),'distinct_final_deck_multisets':len(final_unique),
                   'final_card_base_names':len(final_cards),
                   'compatibility':dict(Counter(r['source_compatibility']['status'] for r in rows)),
                   'raw_groups_with_manifest_fields':sum(bool(r['present_manifest_fields']) for r in rows)},
         'floor_band_caveat':'Repository standard floor ranges, not proof every room/log is complete',
         'field_presence':{k:sum(k in g['run'] for g in groups) for k in field_names},
         'final_card_name_occurrences':dict(sorted(final_cards.items())),
         'entry_vs_final_deck_example':entry_example,'source_build_matrix':matrix,
         'groups':rows,'newly_certified_A_states':0,'training_admitted':False,
         'unresolved':['Exact installed recorder/loader/mod versions are not present in the inspected run metadata.',
                       'No verified historical game-rule manifest links the four build strings to the required transition equivalence.',
                       'No automatic upgrade from field-family matching or endpoint nulls to source certification.'],
         'hashes':{'audit-source-compatibility.py':digest(Path(__file__)),
                   'source_fields.py':digest(PROJECT/'source_fields.py'),
                   'pilot-states.jsonl':digest(PROJECT/'pilot-states.jsonl'),
                   'source-inventory.json':digest(PROJECT/'source-inventory.json')}}
    (PROJECT/'source-compatibility.json').write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(out['counts'],indent=2));print(json.dumps(entry_example,indent=2))


if __name__=='__main__': main()
