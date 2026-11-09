import importlib.util
from pathlib import Path
import pytest
import yaml

path=Path(__file__).resolve().parents[2]/'evals/evaluate.py'
spec=importlib.util.spec_from_file_location('bazi_eval',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def card(**changes):
    out={'four_pillars':['戊辰','戊午','戊申','己未'],'selected_pattern':'土旺泄秀','method_labels':['泄秀'],
        'favorable':['金'],'unfavorable':[],'three_lines':{},'main_percent':50,'report_mode':'preliminary_questions','conditional_judgments':[]}
    out.update(changes);return out


CASES=[{'id':'case','pillars':['戊辰','戊午','戊申','己未'],'label_status':'reviewed',
        'expected':{'required_favorable':['金'],'forbidden_primary_patterns':['从强']}}]


def run(card,model='synthetic-A',repeat=1):return dict(model=model,repeat=repeat,case_id='case',analysis_card=card)


def test_wrong_pillars_and_premature_report_are_hard_failures():
    r=module.evaluate([run(card(four_pillars=['甲子']*4,report_mode='full'))],CASES)
    assert r['hard_failure_runs']==1
    assert set(r['runs'][0]['hard_failures'])>={'four_pillars_mismatch','score_gate_bypassed'}


def test_comparison_separates_within_model_and_between_models():
    r=module.evaluate([run(card()),run(card(),repeat=2),run(card(favorable=['水']),model='synthetic-B')],CASES)
    assert {p['kind'] for p in r['pairs']}=={'within_model','between_models'}
    assert next(p for p in r['pairs'] if p['kind']=='within_model')['exact_field_agreement']==1
    assert r['method_pass_rate']==pytest.approx(2/3)


def test_unreviewed_label_not_used_to_score_method():
    cases=[{**CASES[0],'label_status':'needs_review'}]
    r=module.evaluate([run(card(favorable=[]))],cases)
    assert r['method_pass_rate'] is None
    assert not r['runs'][0]['method_scored']
    with pytest.raises(ValueError):module.evaluate([],cases)


def runxia_card(**changes):
    data=card(four_pillars=['壬子','辛亥','癸丑','壬子'],selected_pattern='润下',method_labels=['润下'],
              favorable=[],conditional_judgments=[{'condition':'原局无食伤','element':'火','judgment':'不利','scope':'本例'}])
    data.update(changes)
    return dict(model='synthetic-model',repeat=1,case_id='DTS-XX-01',analysis_card=data)


def runxia_cases():
    return yaml.safe_load((path.parent/'cases.yaml').read_text())['cases']


def test_confirmed_runxia_case_requires_condition_and_is_scored():
    result=module.evaluate([runxia_card()],runxia_cases())
    assert result['runs'][0]['method_scored']
    assert result['method_pass_rate']==1
    missing=module.evaluate([runxia_card(conditional_judgments=[])],runxia_cases())
    assert 'missing_conditional_judgment' in missing['runs'][0]['method_failures']


def test_runxia_fire_judgment_cannot_be_generalized_to_all_charts():
    judgments=runxia_card()['analysis_card']['conditional_judgments']
    judgments.append({'pattern':'润下','element':'火','judgment':'不利','scope':'全部润下盘'})
    result=module.evaluate([runxia_card(conditional_judgments=judgments)],runxia_cases())
    assert 'forbidden_generalization' in result['runs'][0]['method_failures']
