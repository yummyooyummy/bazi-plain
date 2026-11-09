#!/usr/bin/env python3
"""Two-chart facts only; no compatibility score or relationship predictions."""
import argparse
import json
import sys
from pathlib import Path
from relations import analyze,ten_god


def compare(a,b):
    if a.get('alternative_charts') or b.get('alternative_charts'):
        raise ValueError('有边界备选盘；请先确认采用哪一份，不能静默只取主盘做合盘')
    aa=a['facts']['four_pillars'];bb=b['facts']['four_pillars']
    both={**{f'A{n}':v for n,v in zip(['年','月','日','时'],aa)},**{f'B{n}':v for n,v in zip(['年','月','日','时'],bb)}}
    cross=[x for x in analyze(both) if any(p.startswith('A') for p in x['positions']) and any(p.startswith('B') for p in x['positions'])]
    return {'schema_version':'0.1','scope':'facts_only','relations_between_charts':cross,
        'B_day_stem_relative_to_A':ten_god(aa[2][0],bb[2][0]),'A_day_stem_relative_to_B':ten_god(bb[2][0],aa[2][0]),
        'not_a_compatibility_score':True,'interpretation':'v0.2再验证专门方法；不能据此判断是否适合结婚。'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('a',type=Path);p.add_argument('b',type=Path);args=p.parse_args()
    try:print(json.dumps(compare(json.loads(args.a.read_text()),json.loads(args.b.read_text())),ensure_ascii=False,indent=2))
    except (OSError,ValueError,KeyError) as e:
        print(json.dumps({'status':'invalid_evidence','message':str(e)},ensure_ascii=False));sys.exit(2)
