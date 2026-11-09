"""Late-Zi synthetic coverage and optional external-only private acceptance."""
import json,os,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from paipan import paipan

PRIVATE_PATH=Path(os.environ.get('BAZI_PRIVATE_LATE_ZI_CASES',str(Path.home()/'.local/share/bazi-skill-tests/late_zi_cases.json')))
PRIVATE=json.loads(PRIVATE_PATH.read_text()) if PRIVATE_PATH.exists() else []

def synthetic(time='23:28',zi='split',mode='civil'):
 return paipan({'date':'2000-01-01','time':time,'sex':'male','longitude':120,'timezone':'Asia/Shanghai','as_of':'2026-11-09','zi_method':zi,'clock_mode':mode})

def assert_pair(result):
 assert result['status']=='needs_confirmation'
 assert result['report_gate']['must_confirm_zi_method']
 pair=result['day_convention_comparison']
 assert pair['required'] and pair['same_birth_instant']
 assert {x['zi_method'] for x in pair['charts']}=={'split','23'}
 by_method={x['zi_method']:x for x in pair['charts']}
 assert by_method['split']['day_pillar']!=by_method['23']['day_pillar']
 assert by_method['split']['hour_pillar']==by_method['23']['hour_pillar']
 alt=next(a for a in result['alternative_charts'] if a['reason']=='late_zi_convention')
 assert alt['side']=='same_instant' and alt['same_birth_instant']
 assert alt['zi_method']!=result['conventions']['zi_method']
 assert alt['luck']['start']==result['luck']['start']
 assert alt['facts']['day_independent_check']=='passed'
 assert alt['four_pillars']==alt['facts']['four_pillars']
 assert [r['ganzhi'] for r in alt['annual']]==[r['ganzhi'] for r in result['annual']]
 assert alt['annual'][0]['ten_god']!=result['annual'][0]['ten_god']
 assert len({tuple(a['four_pillars']) for a in result['alternative_charts']})==len(result['alternative_charts'])
 return by_method

@pytest.mark.parametrize('zi',['split','23'])
@pytest.mark.parametrize('time',['23:00','23:01','23:28','23:30','23:31','23:59:59'])
def test_entire_late_hour_always_contains_both_conventions(time,zi):
 r=synthetic(time,zi);pair=assert_pair(r)
 assert pair['split']['day_pillar']=='戊午'
 assert pair['23']['day_pillar']=='己未'
 assert r['facts']['four_pillars']==pair[zi]['four_pillars']

@pytest.mark.parametrize('time',['00:00','00:20','22:59:59','12:00'])
def test_late_hour_is_half_open_not_all_of_zi(time):
 r=synthetic(time)
 assert not r['day_convention_comparison']['required']
 assert not r['report_gate']['must_confirm_zi_method']
 assert not any(a['reason']=='late_zi_convention' for a in r['alternative_charts'])

def test_true_solar_clock_not_civil_hour_controls_comparison():
 not_late=synthetic('23:01',mode='true_solar')
 assert not_late['clock']['calculation_time'].startswith('22:')
 assert not not_late['report_gate']['must_confirm_zi_method']
 solar_late=synthetic('00:02',mode='true_solar')
 assert solar_late['clock']['calculation_time'].startswith('23:')
 assert solar_late['clock']['day_offset_from_civil']==-1
 assert_pair(solar_late)

def test_midnight_sample_is_replaced_by_same_instant_convention():
 r=synthetic('23:59:59');assert_pair(r)
 a=next(a for a in r['alternative_charts'] if a['reason']=='late_zi_convention')
 assert 'day_boundary' in a['also_nearby_reasons']
 assert a['luck']['start']==r['luck']['start']

@pytest.mark.parametrize('case',PRIVATE,ids=[c['id'] for c in PRIVATE])
def test_private_late_zi_acceptance_external_only(case):
 for zi in ['split','23']:
  r=paipan({**case['input'],'zi_method':zi});pair=assert_pair(r)
  assert {k:v['day_pillar'] for k,v in pair.items()}==case['expected_days']
  assert all(x['hour_pillar']==case['expected_hour'] for x in pair.values())

def test_private_late_zi_dates_absent_from_repository():
 if not PRIVATE:pytest.skip('external late-Zi fixture unavailable; local acceptance must load it')
 root=Path(__file__).resolve().parents[2];dates=[c['input']['date'] for c in PRIVATE]
 for p in root.rglob('*'):
  if not p.is_file() or any(x in p.parts for x in ['.git','.venv','__pycache__','.pytest_cache']):continue
  if p.suffix in ['.py','.md','.json','.yaml','.yml','.txt']:
   assert not any(d in p.read_text() for d in dates),'private birthday leaked into repository file'
