#!/usr/bin/env python3
"""Scan an existing evidence packet without re-reading a birthday."""
import argparse
import json
import sys
from pathlib import Path
from paipan import annual_facts

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--start',type=int,required=True)
    p.add_argument('--end',type=int,required=True)
    a=p.parse_args()
    try:
        data=json.loads(a.input.read_text())
        out=annual_facts(a.start,a.end,data['facts']['four_pillars'],data['luck'])
        print(json.dumps({'schema_version':'0.1','annual':out,'not_a_fortune_judgment':True},ensure_ascii=False,indent=2))
    except (OSError,ValueError,KeyError) as e:
        print(json.dumps({'status':'invalid_evidence','message':str(e)},ensure_ascii=False));sys.exit(2)
