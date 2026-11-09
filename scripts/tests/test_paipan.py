import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from paipan import (InputError, annual_start, chart_core, clock_at, get_zone,
                    paipan, resolve_local, from_pillars, city_database, resolve_location)
from relations import analyze, growth, ten_god, validate_pillar, void_branches

PUBLIC=yaml.safe_load((Path(__file__).parent/'golden_cases.yaml').read_text())['cases']
PRIVATE_PATH=Path(os.environ.get('BAZI_PRIVATE_CASES',str(Path.home()/'.local/share/bazi-skill-tests/golden_cases.json')))
PRIVATE=json.loads(PRIVATE_PATH.read_text()) if PRIVATE_PATH.exists() else []


def request(**changes):
    return dict(date='2000-01-01',time='12:00',sex='male',longitude=120,
                timezone='Asia/Shanghai',as_of='2026-11-09',**changes)


@pytest.mark.parametrize('case',PUBLIC,ids=[c['id'] for c in PUBLIC])
def test_public_golden(case):
    assert paipan(case['input'])['facts']['four_pillars']==case['expected']


@pytest.mark.parametrize('case',PRIVATE,ids=[c['id'] for c in PRIVATE])
def test_six_private_golden(case):
    r=paipan({**{k:case[k] for k in ['date','time','city','sex']},'as_of':'2026-11-09','audit':True})
    g=r['facts']['four_pillars']
    if case['expected_pillars']:assert g==case['expected_pillars']
    else:assert g[3]==case['expected_hour']
    if case['id']=='GC01':assert r['clock']['calculation_time'].startswith('16:30:') or r['clock']['calculation_time'].startswith('16:31:')
    if case['id']=='GC02':
        assert r['clock']['day_offset_from_civil']==1
        assert r['luck']['steps'][0]['ganzhi']=='丙午'
        assert r['luck']['steps'][0]['facts']['stem_ten_god']=='劫财'
        alt=paipan({**{k:case[k] for k in ['date','time','city','sex']},'clock_mode':'civil','as_of':'2026-11-09'})
        assert alt['facts']['four_pillars'][2]=='丙辰'
    if case['id']=='GC03':
        assert r['clock']['calculation_time'].startswith('02:22:')
        alt=paipan({**{k:case[k] for k in ['date','time','city','sex']},'clock_mode':'civil','as_of':'2026-11-09'})
        assert alt['facts']['four_pillars'][3]=='戊寅'
    if case['id']=='GC04':
        assert r['clock']['calculation_time'].startswith('10:59:')
        assert any(a['four_pillars'][3]=='戊午' for a in r['alternative_charts'])
        assert any(b['kind']=='hour_boundary' and b['distance_seconds']<=1800 for b in r['boundaries'])


def test_private_fixture_really_has_six_cases():
    if not PRIVATE:pytest.skip('external private fixture unavailable; release acceptance must run it locally')
    assert [c['id'] for c in PRIVATE]==[f'GC{i:02d}' for i in range(1,7)]


def test_private_birth_dates_absent_from_public_tree():
    if not PRIVATE:pytest.skip('external private fixture unavailable')
    forbidden=[c['date'] for c in PRIVATE]
    for folder in ['scripts','references','examples','evals']:
        if not (ROOT/folder).exists():continue
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and p.suffix in ['.py','.md','.json','.yaml','.yml']:
                assert not any(x in p.read_text() for x in forbidden),f'private date leaked into {p.relative_to(ROOT)}'
    for p in ROOT.glob('*'):
        if p.is_file():assert not any(x in p.read_text() for x in forbidden),f'private date leaked into {p.name}'


def test_no_raw_birthday_in_default_evidence():
    r=paipan(request())
    assert '2000-01-01' not in json.dumps(r)
    assert not r['privacy']['raw_birth_date_included']


def test_thirty_minute_threshold_inclusive():
    req=request();req.update(time='14:30',clock_mode='civil')
    r=paipan(req)
    assert any(b['kind']=='hour_boundary' and b['distance_seconds']==1800 for b in r['boundaries'])
    assert len(r['alternative_charts'])>=1
    req['time']='14:29:59';r=paipan(req)
    assert not any(b['name']=='15:00:00' for b in r['boundaries'])


@pytest.mark.parametrize('zone,missing',[('Asia/Shanghai','1986-05-04T02:30:00'),('America/New_York','2024-03-10T02:30:00')])
def test_nonexistent_local_time_rejected(zone,missing):
    with pytest.raises(InputError,match='不存在'):resolve_local(datetime.fromisoformat(missing),zone)


def test_ambiguous_local_time_requires_fold():
    d=datetime.fromisoformat('1991-09-15T01:30:00')
    with pytest.raises(InputError,match='两次|兩次'):resolve_local(d,'Asia/Shanghai')
    assert abs((resolve_local(d,'Asia/Shanghai',1)-resolve_local(d,'Asia/Shanghai',0)).total_seconds())==3600


def test_historical_dst_is_removed_before_solar_correction():
    r=request();r.update(date='1988-07-01')
    out=paipan(r)
    assert out['clock']['dst_seconds']==3600
    assert out['clock']['utc_offset_seconds']==32400
    assert abs(out['clock']['correction_from_civil_seconds']-(out['clock']['equation_of_time_seconds']-3600))<.002


def test_hong_kong_historical_dst_differs_from_mainland():
    d=datetime.fromisoformat('1979-07-01T12:00:00')
    hk=resolve_local(d,'Asia/Hong_Kong');cn=resolve_local(d,'Asia/Shanghai')
    assert (cn-hk).total_seconds()==3600


def test_year_and_month_use_physical_instant_not_solar_clock():
    boundary=annual_start(2000)
    for delta in [-10,10]:
        instant=boundary+timedelta(seconds=delta)
        a=chart_core(instant,{'longitude':0,'timezone':'Etc/UTC'},'male','true_solar','split')[0]
        b=chart_core(instant,{'longitude':170,'timezone':'Asia/Tokyo'},'male','true_solar','split')[0]
        assert a['four_pillars'][:2]==b['four_pillars'][:2]
        assert a['four_pillars'][0]==('己卯' if delta<0 else '庚辰')


def test_near_jie_produces_both_months_and_confirmation_gate():
    instant=(annual_start(2000)-timedelta(seconds=20)).astimezone(get_zone('Asia/Shanghai'))
    r=request();r.update(date=instant.date().isoformat(),time=instant.strftime('%H:%M:%S'))
    out=paipan(r)
    assert out['report_gate']['must_confirm_month']
    assert any(a['four_pillars'][1]!=out['facts']['four_pillars'][1] for a in out['alternative_charts'])
    assert all('crosscheck' in b for b in out['boundaries'] if b['kind']=='jie')


def test_lunar_leap_month_explicit_and_month_thirty_accepted():
    r=request();r.update(calendar='lunar',date='2023-02-01')
    with pytest.raises(InputError,match='is_leap_month'):paipan(r)
    r['is_leap_month']=True
    a=paipan(r);s=request();s.update(date='2023-03-22')
    assert a['facts']['four_pillars']==paipan(s)['facts']['four_pillars']
    r.update(date='2023-02-30',is_leap_month=False)
    assert paipan(r)['status'] in ['calculated','needs_confirmation']


@pytest.mark.parametrize('pillar,expected',[('甲子',['戌','亥']),('甲戌',['申','酉']),('壬辰',['午','未'])])
def test_xunkong(pillar,expected):assert void_branches(pillar)==expected


@pytest.mark.parametrize('day,other,expected',[('甲','己','正财'),('癸','庚','正印'),('戊','辛','伤官'),('乙','丙','伤官')])
def test_ten_gods(day,other,expected):assert ten_god(day,other)==expected


@pytest.mark.parametrize('stem,branch,expected',[('癸','巳','胎'),('壬','巳','绝'),('戊','寅','长生'),('己','酉','长生')])
def test_growth_conventions(stem,branch,expected):assert growth(stem,branch)==expected


def test_clash_and_combine_never_automatically_transform():
    facts=analyze({'年':'甲子','月':'己丑','日':'庚午','时':'丙辰'})
    assert any(x['kind']=='天干合' and x['transformed'] is False for x in facts)
    assert any(x['kind']=='六合' for x in facts)
    assert any(x['kind']=='六冲' for x in facts)


def test_hidden_middle_is_not_added_as_an_existing_branch():
    facts=analyze({'年':'甲申','月':'甲辰'})
    assert any(x['kind']=='拱合候选' and x['missing']=='子' for x in facts)
    assert not any(x['kind']=='三合' for x in facts)


def test_invalid_pillar_rejected():
    with pytest.raises(ValueError):validate_pillar('甲丑')


@pytest.mark.parametrize('field,value',[('longitude',float('nan')),('longitude',181),('zi_method','invented'),('clock_mode','guess'),('time_uncertainty_minutes',-1)])
def test_invalid_inputs_rejected(field,value):
    r=request();r[field]=value
    with pytest.raises((InputError,ValueError)):paipan(r)


def test_pinned_timezone_database():
    r=paipan(request())
    assert r['versions']['tzdata']=='2026.6'
    with pytest.raises(InputError):get_zone('../../etc/passwd')


def test_classical_pillars_never_invent_birth_date_or_luck():
    data=from_pillars(['戊辰','戊午','戊申','己未'])
    assert data['facts']['day_master']=='戊'
    assert data['luck'] is None and data['annual']==[]
    assert data['status']=='facts_only'
    with pytest.raises(ValueError):from_pillars(['甲丑','丙子','戊午','戊午'])


def test_explicit_coordinates_work_even_if_city_missing_from_table():
    r=request();r.update(city='synthetic-offline-location')
    assert paipan(r)['location']['source']=='user_provided'


def test_city_suffix_does_not_silently_switch_to_administrative_centroid():
    a=resolve_location({'city':'扬州'});b=resolve_location({'city':'扬州市'})
    assert a['city_id']==b['city_id']


def test_all_333_prefectural_names_and_four_municipalities_in_published_baseline():
    baseline=json.loads((Path(__file__).parent/'prefecture_names.json').read_text())
    names={s for c in city_database()['cities'] if c['country']=='CN' for s in c['aliases']}
    assert len(baseline['names'])==333
    for name in baseline['names']+baseline['municipalities']:
        variants={name}
        for tail in ['市','地区','自治州']:
            if name.endswith(tail):variants.add(name[:-len(tail)])
        assert variants&names,f'city coverage missing {name}'


def test_boundary_year_luck_segments_cover_contiguous_intervals():
    data=paipan(request())
    steps=data['luck']['steps']
    assert all(a['end_exclusive']==b['start'] for a,b in zip(steps,steps[1:]))
    for year in data['annual']:
        segments=year['luck_segments']
        assert segments
        assert all(a['end_utc_exclusive']==b['start_utc'] for a,b in zip(segments,segments[1:]))
        assert segments[0]['start_utc']==year['start_utc']
        assert segments[-1]['end_utc_exclusive']==year['end_utc_exclusive']
