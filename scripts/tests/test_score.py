import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from score import calculate


def evidence(id,category,side='A',**extra):
    return dict(id=id,category=category,side=side,source='synthetic test evidence',**extra)


def test_confirmed_weights_and_sequence():
    rows=[evidence('hard','hard_condition'),evidence('doubt','doubt'),evidence('event1','history'),evidence('event2','history')]
    result=calculate({'candidates':['顺势型','需要扶持型'],'evidence':rows})
    assert result['candidates'][0]['percent']==90
    assert result['report_mode']=='full'
    assert calculate({'candidates':['顺势型','需要扶持型'],'evidence':list(reversed(rows))})['candidates']==result['candidates']


def test_neutral_events_do_not_increase_confidence():
    r=calculate({'candidates':['A型','B型'],'evidence':[evidence('unknown','history',None)]})
    assert r['main_percent']==50
    assert r['report_mode']=='preliminary_questions'


def test_sixty_percent_gate_and_unresolved_month():
    rows=[evidence('hard','hard_condition'),evidence('doubt','doubt')]
    r=calculate({'candidates':['A型','B型'],'evidence':rows})
    assert r['main_percent']==60 and r['report_mode']=='full_parallel'
    r=calculate({'candidates':['A型','B型'],'evidence':rows,'must_confirm_month':True,'user_declined_questions':True,'questions_offered':True})
    assert r['report_mode']=='preliminary_month_confirmation'


def test_deduplicate_and_reject_conflicts():
    e=evidence('same','history')
    r=calculate({'candidates':['A型','B型'],'evidence':[e,e]})
    assert r['main_percent']==65
    with pytest.raises(ValueError):calculate({'candidates':['A型','B型'],'evidence':[e,{**e,'side':'B'}]})


def test_caps_final_limit_and_negative_events():
    history=[evidence(str(i),'history') for i in range(8)]
    r=calculate({'candidates':['A型','B型'],'evidence':history})
    assert r['candidates'][0]['percent']==95
    cases=[evidence(str(i),'classical_case','B') for i in range(8)]
    r=calculate({'candidates':['A型','B型'],'evidence':cases})
    assert r['candidates'][1]['percent']==70


def test_doubt_never_passes_through_neutral_and_bar_rounds_half_up():
    rows=[evidence('hard','hard_condition')]+[evidence(str(i),'doubt') for i in range(5)]
    assert calculate({'candidates':['A型','B型'],'evidence':rows})['main_percent']==50
    r=calculate({'candidates':['A型','B型'],'evidence':[evidence('hard','hard_condition'),evidence('event','history')]})
    assert r['candidates'][0]['bar'].count('█')==9


def test_prevent_counting_same_judgment_line_twice():
    rows=[evidence('one','line',line='调候'),evidence('two','line',line='调候')]
    with pytest.raises(ValueError):calculate({'candidates':['A型','B型'],'evidence':rows})
