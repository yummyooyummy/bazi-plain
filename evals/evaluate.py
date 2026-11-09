#!/usr/bin/env python3
"""Offline JSON-card comparison. No model calls and no birthday input."""
import argparse
import itertools
import json
from pathlib import Path
import yaml

FIELDS=['selected_pattern','favorable','unfavorable','three_lines','main_percent','report_mode','conditional_judgments']


def normalize(value):
    if isinstance(value,dict):return {k:normalize(v) for k,v in sorted(value.items())}
    if isinstance(value,list):return sorted((normalize(v) for v in value),key=lambda v:json.dumps(v,ensure_ascii=False,sort_keys=True))
    return value


def evaluate(runs,cases):
    if not isinstance(runs,list) or not runs:raise ValueError('需要至少一次实际运行；空结果不能当已评测')
    case_map={c['id']:c for c in cases};out=[]
    for r in runs:
        c=case_map[r['case_id']];a=r.get('analysis_card',{});hard=[];method=[]
        if a.get('four_pillars')!=c['pillars']:hard.append('four_pillars_mismatch')
        for f in FIELDS:
            if f not in a:hard.append('missing_'+f)
        judgments=a.get('conditional_judgments',[])
        if not isinstance(judgments,list) or not all(isinstance(j,dict) for j in judgments):
            hard.append('invalid_conditional_judgments');judgments=[]
        score=a.get('main_percent')
        if not isinstance(score,(int,float)) or isinstance(score,bool) or not 50<=score<=95:hard.append('invalid_main_percent')
        elif score<60 and str(a.get('report_mode','')).startswith('full') and not a.get('confirmed_decline_after_questions'):hard.append('score_gate_bypassed')
        if a.get('month_unconfirmed') and str(a.get('report_mode','')).startswith('full'):hard.append('month_gate_bypassed')
        if a.get('alternate_chart_required') and not a.get('alternate_charts_preserved'):hard.append('alternate_chart_dropped')
        if c.get('label_status')!='needs_review':
            exp=c.get('expected',{})
            for e in exp.get('required_favorable',[]):
                if e not in a.get('favorable',[]):method.append('missing_favorable_'+e)
            for e in exp.get('required_method_labels',[]):
                if e not in a.get('method_labels',[]):method.append('missing_method_'+e)
            for expected in exp.get('required_conditional_judgments',[]):
                if not any(all(j.get(k)==v for k,v in expected.items()) for j in judgments):
                    method.append('missing_conditional_judgment')
            for forbidden in exp.get('forbidden_generalizations',[]):
                if any(all(j.get(k)==v for k,v in forbidden.items()) for j in judgments):
                    method.append('forbidden_generalization')
            if a.get('selected_pattern') in exp.get('forbidden_primary_patterns',[]):method.append('forbidden_primary_pattern')
        out.append({'model':r['model'],'case_id':r['case_id'],'repeat':r['repeat'],'hard_failures':hard,
            'method_scored':c.get('label_status')!='needs_review','method_failures':method,'card':a})
    pairs=[]
    for a,b in itertools.combinations(out,2):
        if a['case_id']!=b['case_id']:continue
        same={f:normalize(a['card'].get(f))==normalize(b['card'].get(f)) for f in FIELDS}
        pairs.append({'case_id':a['case_id'],'kind':'within_model' if a['model']==b['model'] else 'between_models',
            'models':[a['model'],b['model']],'matching_fields':same,'exact_field_agreement':sum(same.values())/len(FIELDS)})
    for r in out:r.pop('card')
    scored=[r for r in out if r['method_scored']]
    return {'runs':out,'pairs':pairs,'hard_failure_runs':sum(bool(r['hard_failures']) for r in out),
        'method_pass_rate':sum(not r['method_failures'] and not r['hard_failures'] for r in scored)/len(scored) if scored else None,
        'not_prediction_accuracy':True,'style_and_ethics_require_separate_review':True}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runs',type=Path,required=True);a=p.parse_args()
    cases=yaml.safe_load((Path(__file__).parent/'cases.yaml').read_text())['cases']
    print(json.dumps(evaluate(json.loads(a.runs.read_text()),cases),ensure_ascii=False,indent=2))
