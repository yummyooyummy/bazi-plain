import copy,fcntl,json,sys
from decimal import Decimal
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pilot_core import (Budget,MODELS,prepare_cases,freeze,parse_json,validate_card,program_decision,final_errors,normalize,compare_runs,screen_report)
import run_pilot
from pilot_prompts import first_messages,second_messages

@pytest.fixture(scope='module')
def cases():return prepare_cases()

def card(payload):
 return {'four_pillars':payload['packet']['facts']['four_pillars'],'strength':{'judgment':'偏强','support':[],'opposition':[]},'special_pattern':{'name':'无','status':'排除'},'structure':{'primary':'待核','changed':'无','assistant':'待定'},'three_lines':{'格局':{},'旺衰':{},'调候':{}},'useful_top_two':[{'rank':1,'elements':['金'],'stems':['庚','辛'],'condition':'教学','scope':'本例'}],'favorable':[],'unfavorable':[],'conditional_judgments':[],'uncertainties':[],'readings':[{'name':'有出口','conditions':[]}],'score_request':None,'fact_citations':[{'pointer':'/packet/facts/four_pillars','value':payload['packet']['facts']['four_pillars']}],'alternatives':[]}

def test_ten_cases_are_8_classical_2_synthetic(cases):
 assert len(cases)==10
 assert sum(x['definition']['kind']=='classical' for x in cases)==8
 assert sum(x['definition']['kind']=='synthetic' for x in cases)==2

def test_payload_has_no_expected_answer_or_raw_input(cases):
 for c in cases:
  p=c['payload'];assert 'checks' not in p and 'definition' not in p and 'input' not in p
  if c['definition']['kind']=='synthetic':assert c['definition']['input']['date'] not in json.dumps(p,ensure_ascii=False)

def test_frozen_inputs_reject_changes(tmp_path,monkeypatch):
 freeze(tmp_path);m=tmp_path/'manifest.json';d=json.loads(m.read_text());d['materials_sha256']='modified';m.write_text(json.dumps(d))
 with pytest.raises(ValueError,match='changed'):freeze(tmp_path)

def test_json_parser_does_not_extract_or_execute_code():
 assert parse_json('```json\n{"x":1}\n```')=={'x':1}
 for t in ['[]','explanation {"x":1}','__import__("os")']:
  with pytest.raises(ValueError):parse_json(t)

def test_fact_citation_values_must_match(cases):
 p=cases[0]['payload'];c=card(p);assert validate_card(c,p)==[]
 c['fact_citations'][0]['value']=['invented'];assert 'R1_invalid_fact_citation' in validate_card(c,p)

def test_citation_path_cannot_escape_payload(cases):
 p=cases[0]['payload'];c=card(p);c['fact_citations'][0]['pointer']='../../secret'
 assert 'R1_invalid_fact_citation' in validate_card(c,p)

def test_wrong_chart_rejected(cases):
 p=cases[0]['payload'];c=card(p);c['four_pillars']=['甲子']*4
 assert 'R1_four_pillars_mismatch' in validate_card(c,p)

def test_hour_boundary_alternative_required(cases):
 p=cases[-1]['payload'];c=card(p)
 assert len(p['packet']['alternative_charts'])==1
 assert 'R4_alternative_chart_dropped' in validate_card(c,p)
 c['alternatives']=[{'four_pillars':p['packet']['alternative_charts'][0]['four_pillars']}]
 assert validate_card(c,p)==[]
 d=program_decision(c,p);assert d['report_mode'].endswith('omit_hour_dependent_sections')

def test_single_reading_has_no_invented_percent(cases):
 p=cases[0]['payload'];c=card(p);d=program_decision(c,p)
 assert d['main_percent'] is None and d['tendency_band']=='not_applicable_single_reading'
 c['score_request']={}
 with pytest.raises(ValueError):program_decision(c,p)

def test_score_must_use_local_script_and_not_fake_confirmation(cases):
 p=cases[0]['payload'];c=card(p);c['readings']=[{'name':'A'},{'name':'B'}]
 c['score_request']={'candidates':['A','B'],'evidence':[{'id':'d1','category':'doubt','source':'S03-08'}],'questions_offered':True,'user_declined_questions':True}
 d=program_decision(c,p);assert d['main_percent']==50 and d['report_mode']=='preliminary_questions'

def test_history_not_invented(cases):
 p=cases[0]['payload'];c=card(p);c['readings']=[{'name':'A'},{'name':'B'}]
 c['score_request']={'candidates':['A','B'],'evidence':[{'id':'h','category':'history','side':'A','source':'invented'}]}
 with pytest.raises(ValueError,match='historical'):program_decision(c,p)

def test_stage_B_cannot_change_core_judgment(cases):
 p=cases[0]['payload'];a=card(p);d=program_decision(a,p);b={**copy.deepcopy(a),**{k:d[k] for k in ['main_percent','tendency_band','report_mode']}}
 assert final_errors(a,b,d,p)==[]
 b['strength']['judgment']='偏弱';assert 'stage_B_changed_strength' in final_errors(a,b,d,p)

def test_month_gate_overrides_single_reading(cases):
 p=copy.deepcopy(cases[0]['payload']);p['packet']['report_gate']['must_confirm_month']=True
 assert program_decision(card(p),p)['report_mode']=='preliminary_month_confirmation'

def test_normalization_preserves_rank_and_conditional_scope():
 assert normalize(['水','木'],'favorable')==normalize(['木','水'],'favorable')
 assert normalize('从旺')!=normalize('从强')
 assert normalize([{'rank':1,'elements':['金']},{'rank':2,'elements':['水']}],'useful_top_two')!=normalize([{'rank':2,'elements':['金']},{'rank':1,'elements':['水']}],'useful_top_two')
 assert normalize({'scope':'本例'})!=normalize({'scope':'全部润下盘'})

def test_comparison_denominators_include_missing_models(cases):
 p=cases[0]['payload'];c=card(p);c.update(tendency_band='60%-79%',report_mode='full_parallel')
 rows=[{'case_id':'M01','provider':x,'analysis_card':copy.deepcopy(c),'hard_failures':[]} for x in ['claude','gpt']]
 out=compare_runs(rows,cases[:1]);r=out['fields']['strength']
 assert r['matches']==1 and r['comparisons']==3 and len(r['differences'])==2
 assert out['same_model_repeat_agreement'] is None

def test_invalid_card_not_counted_as_matching(cases):
 p=cases[0]['payload'];c=card(p)
 rows=[{'case_id':'M01','provider':x,'analysis_card':copy.deepcopy(c),'hard_failures':['R1']} for x in MODELS]
 assert compare_runs(rows,cases[:1])['fields']['strength']['matches']==0

def test_legitimate_NA_separate_from_valid_agreement(cases):
 c=card(cases[0]['payload']);c['tendency_band']='not_applicable_single_reading'
 rows=[{'case_id':'M01','provider':x,'analysis_card':copy.deepcopy(c),'hard_failures':[]} for x in MODELS]
 r=compare_runs(rows,cases[:1])['fields']['tendency_band'];assert r['comparisons']==0 and r['not_applicable']==3 and r['agreement'] is None

def test_budget_pre_reserves_unknown_cost_and_survives_reload(tmp_path):
 path=tmp_path/'ledger.json';b=Budget(path);b.reserve('1','claude',80000,12000)
 assert b.committed()==Decimal('.32')
 assert Budget(path).committed()==Decimal('.32')
 b.settle('1',10000,1000);assert b.committed()==Decimal('.03')
 with pytest.raises(ValueError,match='duplicate'):b.reserve('1','gpt',80000,12000)

def test_budget_stops_before_15_dollars_and_no_writes_on_reject(tmp_path):
 b=Budget(tmp_path/'budget.json')
 for i in range(41):b.reserve(str(i),'claude',80000,16000)
 assert b.committed()==Decimal('14.76')
 n=len(b.data['attempts'])
 with pytest.raises(ValueError,match='15 USD'):b.reserve('over','claude',80000,16000)
 assert len(b.data['attempts'])==n

def test_attempt_and_retry_caps_enforced(tmp_path):
 b=Budget(tmp_path/'a.json')
 for i in range(60):b.reserve(str(i),'deepseek',1,12000)
 for i in range(60,66):b.reserve(str(i),'deepseek',1,12000,retry=True)
 with pytest.raises(ValueError,match='66'):b.reserve('67','deepseek',1,12000)
 b=Budget(tmp_path/'b.json')
 for i in range(6):b.reserve(str(i),'deepseek',1,12000,retry=True)
 with pytest.raises(ValueError,match='6 retry'):b.reserve('7','deepseek',1,12000,retry=True)

def test_negative_usage_and_cache_creation_underestimate_rejected(tmp_path):
 b=Budget(tmp_path/'b.json');b.reserve('x','claude',80000,12000)
 with pytest.raises(ValueError):b.settle('x',-1,1)
 b.settle('x',80000,12000,80000);assert b.committed()==Decimal('.32')

def test_budget_caps_cannot_be_modified_in_saved_ledger(tmp_path):
 p=tmp_path/'b.json';p.write_text(json.dumps({'cap_usd':'100','max_attempts':66,'max_retries':6}))
 with pytest.raises(ValueError,match='unapproved'):Budget(p)

def test_transport_bodies_have_explicit_output_caps_and_no_tools():
 for provider in MODELS:
  b=run_pilot.request_body(provider,'system',[{'role':'user','content':'JSON'}],12000)
  assert b.get('max_output_tokens',b.get('max_tokens'))==12000
  assert 'temperature' not in b
  if provider=='gpt':assert b['store'] is False and b['tools']==[]

def test_extract_total_usage_includes_cache_and_reasoning():
 g={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'{}'}]}],'usage':{'input_tokens':5,'output_tokens':9,'output_tokens_details':{'reasoning_tokens':7}}}
 assert run_pilot.extract('gpt',g)==('{}',5,9,True)
 a={'stop_reason':'end_turn','content':[{'type':'thinking','thinking':'hidden'},{'type':'text','text':'{}'}],'usage':{'input_tokens':5,'cache_read_input_tokens':10,'cache_creation_input_tokens':2,'output_tokens':9}}
 assert run_pilot.extract('claude',a)==('{}',17,9,True)

def test_no_secret_or_network_needed_for_preparation(tmp_path,monkeypatch):
 monkeypatch.setattr(run_pilot,'credentials',lambda:{p:'' for p in MODELS})
 monkeypatch.setattr(run_pilot,'http',lambda *a,**k:pytest.fail('network must not run without credentials'))
 result=run_pilot.run(tmp_path,execute=True)
 assert result['status']=='awaiting_credentials' and result['generation_calls']==0
 b=json.loads((tmp_path/'budget.json').read_text());assert b['attempts']==[]
 report=json.loads((tmp_path/'summary.json').read_text());assert report['fields'] is None and report['agreement_status']=='not_started_no_results'

def test_existing_run_lock_prevents_another_runner(tmp_path):
 with (tmp_path/'.run.lock').open('a') as f:
  fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
  with pytest.raises(run_pilot.StopPilot,match='Another'):run_pilot.run(tmp_path,False)

def test_report_screen_is_only_triage():
 flags=screen_report('不写克夫。传统五行对应肾；体检。',{})
 assert flags and all(f['status']=='needs_human_review' for f in flags)

def test_stage_B_receives_only_own_card_and_program_decision(cases):
 a=card(cases[0]['payload']);d=program_decision(a,cases[0]['payload'])
 system,messages=second_messages('material',cases[0]['payload'],json.dumps(a),d)
 assert messages[-2]['role']=='assistant' and json.loads(messages[-2]['content'])==a
 assert 'program_decision' in messages[-1]['content']
 assert 'checks' not in messages[0]['content']

def test_deepseek_cash_reservation_uses_byte_bound(tmp_path):
 b=Budget(tmp_path/'budget.json');b.reserve('x','deepseek',80000,12000,billing_input_upper=200000)
 assert b.committed()==Decimal('.0744')

def test_formal_generation_limit_is_60_even_without_retries(tmp_path):
 b=Budget(tmp_path/'budget.json')
 for i in range(60):b.reserve(str(i),'deepseek',1,12000)
 with pytest.raises(ValueError,match='60 formal'):b.reserve('61','deepseek',1,12000)

def test_entire_30_slot_two_phase_pipeline_offline(tmp_path,monkeypatch):
 # This is a mocked local integration test, never a multi-model evaluation result.
 monkeypatch.setattr(run_pilot,'credentials',lambda:{p:'testing-placeholder-not-a-key' for p in MODELS})
 monkeypatch.setattr(run_pilot,'check_access',lambda keys:{p:{'available':True} for p in MODELS})
 monkeypatch.setattr(run_pilot,'http',lambda *a,**k:pytest.fail('network prohibited in integration test'))
 calls=[]
 def fake_generate(provider,system,messages,stage,slot,keys,run_dir,budget):
  calls.append((slot,stage))
  payload=json.loads(messages[0]['content'].split('事实包：\n',1)[1])
  if stage=='A':
   c=card(payload);c.update(main_percent=None,tendency_band='pending_program',report_mode='pending_program')
   c['alternatives']=[{'four_pillars':a['four_pillars']} for a in payload['packet']['alternative_charts']]
   return json.dumps(c,ensure_ascii=False)
  c=json.loads(messages[-2]['content']);d=json.loads(messages[-1]['content'].split('program_decision：\n',1)[1])
  c.update({k:d[k] for k in ['main_percent','tendency_band','report_mode']})
  return json.dumps({'analysis_card':c,'report_markdown':'本地模拟输出，不是模型评测结果。'},ensure_ascii=False)
 monkeypatch.setattr(run_pilot,'generate',fake_generate)
 r=run_pilot.run(tmp_path,execute=True)
 assert r['status']=='complete' and len(r['results'])==30 and len(calls)==60
 assert all(not x['hard_failures'] for x in r['results'])
 assert r['generation_attempts']==0  # mock never touched a provider or reserve ledger
 assert r['same_model_repeat_status']=='not_tested_single_run'
