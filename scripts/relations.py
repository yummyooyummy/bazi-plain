#!/usr/bin/env python3
"""Deterministic stem/branch structures. Never infer transformation or fortune."""
from __future__ import annotations
import argparse
import itertools
import json
from pathlib import Path

TABLES = json.loads((Path(__file__).resolve().parent/'data/tables.json').read_text())
STEMS, BRANCHES = TABLES['stems'], TABLES['branches']


def validate_pillar(pillar):
    if not isinstance(pillar,str) or len(pillar)!=2 or pillar[0] not in STEMS or pillar[1] not in BRANCHES:
        raise ValueError('干支必須是有效的兩字柱')
    if STEMS.index(pillar[0])%2 != BRANCHES.index(pillar[1])%2:
        raise ValueError('干支陰陽不配，該柱不在六十甲子中')
    return pillar


def ten_god(day_stem, other_stem):
    try:return TABLES['ten_gods'][day_stem+other_stem]
    except KeyError:raise ValueError('十神查詢需要兩個有效天干')


def growth(day_stem, branch):
    gi,zi=STEMS.index(day_stem),BRANCHES.index(branch)
    offset=TABLES['growth_offsets'][day_stem]
    return TABLES['growth_stages'][(offset+(zi if gi%2==0 else -zi))%12]


def void_branches(pillar):
    validate_pillar(pillar)
    n=next(i for i in range(60) if STEMS[i%10]+BRANCHES[i%12]==pillar)
    start=(n//10)*10
    return [BRANCHES[(start+10)%12],BRANCHES[(start+11)%12]]


def analyze(pillars):
    """Input is a mapping of position labels to valid pillars."""
    pairs=list(pillars.items())
    for _,p in pairs:validate_pillar(p)
    output=[]
    def add(kind, positions, values, **extra):
        output.append(dict(kind=kind,positions=list(positions),values=list(values),**extra))
    for (pa,a),(pb,b) in itertools.combinations(pairs,2):
        positions=[pa,pb]; gs={a[0],b[0]};zs={a[1],b[1]}
        if a==b:add('伏吟',positions,[a,b])
        if a[0]==b[0]:add('同干',positions,[a[0],b[0]])
        for x,y,el in TABLES['stem_combine']:
            if gs=={x,y}:add('天干合',positions,[a[0],b[0]],possible_element=el,transformed=False)
        for x,y in TABLES['stem_opposition']:
            if gs=={x,y}:add('天干冲',positions,[a[0],b[0]])
        for key,label in [('branch_combine','六合'),('branch_clash','六冲'),('branch_harm','六害'),('branch_break','六破'),('mutual_punishment','相刑')]:
            if any(zs==set(group) for group in TABLES[key]):add(label,positions,[a[1],b[1]])
        if a[1]==b[1] and a[1] in TABLES['self_punishment']:add('自刑',positions,[a[1],b[1]])
        if len(zs)==2 and any(zs<set(group) for group in TABLES['punishment_groups']):add('刑（两支）',positions,[a[1],b[1]])
        for group,el in TABLES['triple_combine']:
            if len(zs)==2 and zs<set(group):
                if group[1] in zs:add('半合',positions,[a[1],b[1]],possible_element=el,transformed=False)
                else:add('拱合候选',positions,[a[1],b[1]],missing=group[1],same_stem=a[0]==b[0],transformed=False)
        delta=(BRANCHES.index(b[1])-BRANCHES.index(a[1]))%12
        if a[0]==b[0] and delta in [2,10]:
            middle=BRANCHES[(BRANCHES.index(a[1])+(1 if delta==2 else -1))%12]
            add('同干夹字候选',positions,[a,b],missing=middle,counts_as_present=False)
        if any(zs==set(g) for g in TABLES['branch_clash']):
            ea=TABLES['stem_elements'][a[0]];eb=TABLES['stem_elements'][b[0]]
            order='木火土金水'
            if (order.index(eb)-order.index(ea))%5 in [2,3]:
                add('天克地冲（反吟候选）',positions,[a,b],definition='干相克且支相冲，不直接判吉凶')
    for triple in itertools.combinations(pairs,3):
        ps=[x[0] for x in triple];bs=[x[1][1] for x in triple]
        if len(set(bs))!=3:continue
        for key,label in [('triple_combine','三合'),('triple_meeting','三会')]:
            for group,el in TABLES[key]:
                if set(bs)==set(group):add(label,ps,bs,possible_element=el,transformed=False)
        for group in TABLES['punishment_groups']:
            if set(bs)==set(group):add('三刑齐',ps,bs)
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pillars',nargs='+')
    args=parser.parse_args()
    try:print(json.dumps({'relations':analyze({f'柱{i+1}':p for i,p in enumerate(args.pillars)}),'not_a_fortune_judgment':True},ensure_ascii=False,indent=2))
    except ValueError as e:parser.error(str(e))
