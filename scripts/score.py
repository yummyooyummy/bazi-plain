#!/usr/bin/env python3
"""Deterministic tendency points and the user-confirmed report gate.

These percentages are a bookkeeping convention, not statistical probabilities.
"""
import argparse
import json
import sys
from pathlib import Path

ORDER=['hard_condition','classical_case','line','doubt','history']
LINES={'格局','旺衰','调候'}


def calculate(request):
    if not isinstance(request,dict):raise ValueError('计分输入须为JSON对象')
    names=request.get('candidates')
    if not isinstance(names,list) or len(names)!=2 or not all(isinstance(s,str) and s for s in names) or names[0]==names[1]:
        raise ValueError('需要两个不重复、普通人能理解的候选名称')
    evidence=request.get('evidence',[]);unique={};duplicates=[]
    if not isinstance(evidence,list) or not all(isinstance(x,dict) for x in evidence):raise ValueError('evidence须为对象数组')
    for flag in ['must_confirm_month','questions_offered','user_declined_questions','time_unconfirmed']:
        if flag in request and not isinstance(request[flag],bool):raise ValueError('闸门标志必须是布尔值')
    for item in evidence:
        ident=item.get('id')
        if not isinstance(ident,str) or not ident:raise ValueError('每条证据必须有唯一id')
        if ident in unique:
            if unique[ident]!=item:raise ValueError('同一证据id出现互相矛盾的内容')
            duplicates.append(ident);continue
        if item.get('category') not in ORDER:raise ValueError('证据类别不受支持')
        if item['category']!='doubt' and item.get('side') not in ['A','B',None]:raise ValueError('side须为A、B或null')
        if not item.get('source'):raise ValueError('每条证据必须有出处或已确认事件的本地编号')
        if item['category']=='line' and item.get('line') not in LINES:raise ValueError('三线仅限格局、旺衰、调候')
        unique[ident]=item
    points=50;trace=[];seen_hard=set();seen_lines=set()
    for category in ORDER:
        rows=sorted((v for v in unique.values() if v['category']==category),key=lambda x:x['id'])
        if category in ['classical_case','history']:
            before=points;weight=10 if category=='classical_case' else 15;cap=20 if category=='classical_case' else 45
            delta=sum(weight if r.get('side')=='A' else -weight if r.get('side')=='B' else 0 for r in rows)
            delta=max(-cap,min(cap,delta));points+=delta
            trace.append({'category':category,'ids':[r['id'] for r in rows],'before':before,'delta_A':delta,'after':points,'cap':cap})
            continue
        for r in rows:
            before=points;side=r.get('side')
            if category=='hard_condition':
                if side in seen_hard:raise ValueError('每候选的硬条件最多记一次20分；请合并证据')
                if side is not None:seen_hard.add(side);points+=20 if side=='A' else -20
            elif category=='line':
                if r['line'] in seen_lines:raise ValueError('同一判断线不能重复计分')
                seen_lines.add(r['line'])
                points+=5 if side=='A' else -5 if side=='B' else 0
            else:
                points+=min(10,50-points) if points<50 else -min(10,points-50)
            trace.append({'category':category,'id':r['id'],'source':r['source'],'before':before,'delta_A':points-before,'after':points})
    raw=points;points=max(5,min(95,points));scores=[points,100-points];dominant=max(scores)
    main=0 if scores[0]>=scores[1] else 1
    mode='full' if dominant>=80 else 'full_parallel' if dominant>=60 else 'preliminary_questions'
    if request.get('must_confirm_month'):mode='preliminary_month_confirmation'
    elif request.get('questions_offered') and request.get('user_declined_questions'):
        mode='full_conditional' if mode=='preliminary_questions' else mode
    if request.get('time_unconfirmed') and mode.startswith('full'):mode+='__omit_hour_dependent_sections'
    return {'schema_version':'0.1','tendency_score_not_probability':True,
        'candidates':[{'id':side,'name':name,'percent':s,'bar':'█'*((s+5)//10)+'░'*(10-(s+5)//10)} for side,name,s in zip(['A','B'],names,scores)],
        'main_candidate':['A','B'][main],'main_percent':dominant,'report_mode':mode,
        'raw_A_before_final_limit':raw,'trace':trace,'duplicate_ids_ignored':duplicates,
        'order':ORDER,'evidence':list(unique.values())}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path);a=p.parse_args()
    try:print(json.dumps(calculate(json.loads(a.input.read_text() if a.input else sys.stdin.read())),ensure_ascii=False,indent=2))
    except (OSError,ValueError,TypeError) as e:
        print(json.dumps({'status':'invalid_scoring_input','message':str(e)},ensure_ascii=False));sys.exit(2)
