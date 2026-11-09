#!/usr/bin/env python3
"""Approved local pilot. Default prepares inputs and checks credentials, with no network.

Only --execute can generate; official APIs only, hard $15 cap and <=66 attempts.
Credentials: environment or ~/.config/bazi-skill/credentials.env (mode 600).
"""
from __future__ import annotations
import argparse,fcntl,hashlib,json,math,os,sys,time,urllib.error,urllib.request
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
from pilot_core import (ROOT,MODELS,REQUIRED,Budget,freeze,canonical,digest,parse_json,
 validate_card,program_decision,final_errors,compare_runs,screen_report)
from pilot_prompts import first_messages,second_messages

DEFAULT_DIR=Path.home()/'.local/share/bazi-skill-evals/pilot-20261109'
CREDENTIALS=Path.home()/'.config/bazi-skill/credentials.env'
TOKENIZER=Path.home()/'.cache/bazi-skill/deepseek-v4-tokenizer/tokenizer.json'
class StopPilot(Exception):pass
class RequestFailure(Exception):
 def __init__(self,status=None,retryable=False):
  super().__init__('HTTP request failed'+(' ('+str(status)+')' if status else ''));self.status=status;self.retryable=retryable

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None

def write_json(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
 tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');tmp.chmod(0o600);tmp.replace(path)

def credentials():
 result={k:os.environ.get(m['key'],'').strip() for k,m in MODELS.items()}
 if CREDENTIALS.is_file():
  if CREDENTIALS.stat().st_mode & 0o077:raise StopPilot('Private credential file must have mode 600')
  values={}
  for line in CREDENTIALS.read_text().splitlines():
   line=line.strip()
   if not line or line.startswith('#'):continue
   if '=' not in line:raise StopPilot('Credential file requires KEY=value lines (never shell code)')
   key,value=line.split('=',1);key=key.strip();value=value.strip()
   if value[:1] in ['"',"'"] and value[-1:]==value[:1]:value=value[1:-1]
   if key in [m['key'] for m in MODELS.values()]:values[key]=value
  for provider,m in MODELS.items():result[provider]=result[provider] or values.get(m['key'],'')
 return result

def http(provider,key,path,body=None):
 # Reject all redirects, custom hosts and query secrets. No raw headers/errors logged.
 url=MODELS[provider]['base']+path
 headers={'Content-Type':'application/json','User-Agent':'bazi-skill-approved-pilot/1'}
 if provider=='claude':headers.update({'x-api-key':key,'anthropic-version':'2023-06-01'})
 else:headers['Authorization']='Bearer '+key
 req=urllib.request.Request(url,data=json.dumps(body,ensure_ascii=False).encode() if body is not None else None,headers=headers,method='POST' if body is not None else 'GET')
 opener=urllib.request.build_opener(NoRedirect())
 try:
  with opener.open(req,timeout=300) as response:
   raw=response.read(12_000_001)
   if len(raw)>12_000_000:raise StopPilot('Response exceeds local size cap')
   data=json.loads(raw)
   return data,{'request_id':response.headers.get('x-request-id') or response.headers.get('request-id')}
 except urllib.error.HTTPError as e:raise RequestFailure(e.code,e.code in [408,429,500,502,503,504]) from None
 except (urllib.error.URLError,TimeoutError,ConnectionError):raise RequestFailure(None,True) from None

def preflight(keys):
 missing=[MODELS[p]['key'] for p,v in keys.items() if not v]
 if missing:return {'status':'awaiting_credentials','missing':missing,'generation_calls':0,'model_access':'not_checked_without_all_credentials'}
 return {'status':'credentials_present_access_unverified','generation_calls':0}

def check_access(keys):
 checks={}
 for provider,m in MODELS.items():
  path='/v1/models' if provider in ['claude','gpt'] else '/models'
  data,_=http(provider,keys[provider],path)
  visible=[r.get('id') for r in data.get('data',[])]
  checks[provider]={'model':m['id'],'available':m['id'] in visible}
 if not all(v['available'] for v in checks.values()):raise StopPilot('Approved model missing from model list; no substitution or generation')
 return checks

def request_body(provider,system,messages,cap):
 m=MODELS[provider]['id']
 if provider=='gpt':return {'model':m,'instructions':system,'input':messages,'reasoning':{'effort':'medium'},'max_output_tokens':cap,'store':False,'truncation':'disabled','tools':[]}
 if provider=='claude':return {'model':m,'system':system,'messages':messages,'thinking':{'type':'adaptive'},'output_config':{'effort':'medium'},'max_tokens':cap}
 return {'model':m,'messages':[{'role':'system','content':system}]+messages,'thinking':{'type':'enabled'},'reasoning_effort':'high','max_tokens':cap,'response_format':{'type':'json_object'},'stream':False}

def count_input(provider,key,system,messages):
 if provider=='gpt':
  data,_=http(provider,key,'/v1/responses/input_tokens',{'model':MODELS[provider]['id'],'instructions':system,'input':messages})
  n=data['input_tokens'];method='official_count_endpoint'
 elif provider=='claude':
  data,_=http(provider,key,'/v1/messages/count_tokens',{'model':MODELS[provider]['id'],'system':system,'messages':messages,'thinking':{'type':'adaptive'}})
  n=data['input_tokens'];method='official_count_endpoint'
 else:
  # Official tokenizer JSON is data only; never execute remote Python/trust_remote_code.
  if not TOKENIZER.is_file():raise StopPilot('Official DeepSeek tokenizer data missing')
  from tokenizers import Tokenizer
  tokenizer=Tokenizer.from_file(str(TOKENIZER))
  strings=[system]+[x['content'] for x in messages]
  actual=sum(len(tokenizer.encode(x,add_special_tokens=False).ids) for x in strings)
  n=math.ceil(actual*1.20)+1024
  method='official_local_tokenizer_plus_20_percent_and_1024_not_exact'
 if isinstance(n,bool) or not isinstance(n,int) or n<1 or n>80000:raise StopPilot('Input count exceeds approved 80k guard; no truncation or generation')
 # Reserve full 80k even when measured shorter; discounts never needed for protection.
 return 80000,{'measured_or_guarded_input_tokens':n,'method':method}

def extract(provider,data):
 if provider=='gpt':
  text=''.join(c.get('text','') for o in data.get('output',[]) if o.get('type')=='message' for c in o.get('content',[]) if c.get('type')=='output_text')
  u=data.get('usage',{});return text,u.get('input_tokens'),u.get('output_tokens'),data.get('status')=='completed'
 if provider=='claude':
  text=''.join(c.get('text','') for c in data.get('content',[]) if c.get('type')=='text')
  u=data.get('usage',{});inp=sum(u.get(k,0) for k in ['input_tokens','cache_creation_input_tokens','cache_read_input_tokens'])
  return text,inp,u.get('output_tokens'),data.get('stop_reason')=='end_turn'
 choice=data.get('choices',[{}])[0];u=data.get('usage',{})
 return choice.get('message',{}).get('content',''),u.get('prompt_tokens'),u.get('completion_tokens'),choice.get('finish_reason')=='stop'

def generate(provider,system,messages,stage,slot,keys,run_dir,budget):
 cap=12000 if stage=='A' else 16000
 upper,count_meta=count_input(provider,keys[provider],system,messages)
 path={'claude':'/v1/messages','gpt':'/v1/responses','deepseek':'/chat/completions'}[provider]
 for attempt in range(2):
  ident=slot+'-'+stage+'-'+str(attempt+1)
  byte_guard=len(system.encode())+sum(len(x['content'].encode()) for x in messages)+4096
  try:budget.reserve(ident,provider,upper,cap,retry=attempt>0,billing_input_upper=max(upper,byte_guard) if provider=='deepseek' else upper)
  except ValueError as e:raise StopPilot(str(e)) from None
  out=run_dir/'requests'/str(ident+'.json')
  body=request_body(provider,system,messages,cap)
  write_json(out,{'request_sha256':digest(canonical(body)),'count':count_meta,'model':MODELS[provider]['id'],'status':'reserved_not_confirmed','stage':stage})
  started=time.monotonic()
  try:
   response,meta=http(provider,keys[provider],path,body)
  except RequestFailure as e:
   write_json(out,{'status':'transport_failed_unknown_billing','http_status':e.status,'elapsed_seconds':time.monotonic()-started,'stage':stage,'model':MODELS[provider]['id']})
   if e.retryable and attempt==0:
    time.sleep(2);continue
   raise
  text,inp,output,complete=extract(provider,response)
  # Record response before parsing/settling. Even malformed outputs remain billable evidence.
  write_json(out,{'status':'received','raw_response':response,'meta':meta,'elapsed_seconds':time.monotonic()-started,'stage':stage,'model':MODELS[provider]['id'],'count':count_meta})
  if any(isinstance(n,bool) or not isinstance(n,int) or n<0 for n in [inp,output]):raise StopPilot('Missing valid usage; reservation retained, no further generation')
  if inp>80000 or output>cap:raise StopPilot('Actual usage exceeds input/output guard; reservation retained, stop')
  u=response.get('usage',{})
  writes=u.get('cache_creation_input_tokens',0) if provider=='claude' else u.get('input_tokens_details',{}).get('cache_creation_tokens',0) if provider=='gpt' else 0
  try:budget.settle(ident,inp,output,writes)
  except ValueError as e:raise StopPilot(str(e)) from None
  if not complete:raise StopPilot('Truncated/refused response retained; no automatic continuation')
  if not text.strip():raise StopPilot('Empty model output retained; no repair call')
  return text
 raise StopPilot('Request not completed')

def summary(run_dir,cases,runs,budget,status):
 report=compare_runs(runs,cases)
 if not runs:
  report['fields']=None
  report['agreement_status']='not_started_no_results'
 report.update(status=status,generation_attempts=len(budget.data['attempts']),cost_committed_usd=str(budget.committed()),budget_cap_usd='15',results=runs)
 write_json(run_dir/'summary.json',report)
 # Raw provider outputs are kept locally, never embedded in this public repository.
 text=['# 试测状态','',f'状态：{status}',f'有效结果记录：{len(runs)}/30；生成尝试：{len(budget.data["attempts"])}/66。',f'费用保守计入（含未知费用预留）：${budget.committed()}，上限$15。','同模型重复稳定性：未测。人工伦理复核：尚未完成。','']
 if status!='complete':text+=['尚未完成30份，不据此报告已完成的跨模型总体一致率。','']
 else:
  for field,row in report['fields'].items():text.append(f'- {field}：{row["matches"]}/{row["comparisons"]}；不适用{row["not_applicable"]}对。')
 (run_dir/'状态.md').write_text('\n'.join(text)+'\n');(run_dir/'状态.md').chmod(0o600)
 return report

def _run_locked(run_dir,execute=False):
 run_dir=Path(run_dir);material,cases=freeze(run_dir)
 keys=credentials();pf=preflight(keys);write_json(run_dir/'preflight.json',pf)
 budget=Budget(run_dir/'budget.json');budget.save()
 result_path=run_dir/'runs.json';runs=json.loads(result_path.read_text()) if result_path.exists() else []
 if pf['status']=='awaiting_credentials':
  summary(run_dir,cases,runs,budget,'awaiting_credentials');return pf
 if not execute:
  summary(run_dir,cases,runs,budget,'prepared_no_network');return pf
 access=check_access(keys);write_json(run_dir/'access.json',access)
 completed={(r['case_id'],r['provider']) for r in runs}
 if any(a.get('status')=='reserved_unknown' for a in budget.data['attempts']):
  raise StopPilot('An earlier attempt has unknown billing/outcome; reconcile before resuming')
 # Case-first means the three initial slots are the same M01, not 10 Claude calls first.
 try:
  for case in cases:
   for provider in MODELS:
    cid=case['definition']['id'];slot=cid+'-'+provider
    if (cid,provider) in completed:continue
    payload=case['payload'];system,messages=first_messages(material,payload)
    first=generate(provider,system,messages,'A',slot,keys,run_dir,budget)
    try:card=parse_json(first)
    except (ValueError,TypeError):raise StopPilot('Stage A JSON invalid; paid failure preserved, stop for inspection')
    errors=validate_card(card,payload)
    if 'main_percent' not in card or card.get('main_percent') is not None or card.get('tendency_band')!='pending_program' or card.get('report_mode')!='pending_program':errors.append('R6_stage_A_must_wait_for_program')
    if errors:
     runs.append({'case_id':cid,'provider':provider,'model':MODELS[provider]['id'],'status':'invalid_stage_A','hard_failures':errors,'analysis_card':card})
     write_json(result_path,runs);raise StopPilot('Stage A schema/facts failed; stop before spending on report')
    try:decision=program_decision(card,payload)
    except (ValueError,KeyError,TypeError):raise StopPilot('Invalid score request; no repair or report call')
    write_json(run_dir/'decisions'/str(slot+'.json'),decision)
    system,messages=second_messages(material,payload,first,decision)
    second=generate(provider,system,messages,'B',slot,keys,run_dir,budget)
    try:
     output=parse_json(second);final=output['analysis_card'];report=output['report_markdown']
     if not isinstance(final,dict) or not isinstance(report,str):raise ValueError('invalid output')
    except (ValueError,KeyError,TypeError):raise StopPilot('Stage B format failed; raw output retained, no repair')
    errors=final_errors(card,final,decision,payload)
    runs.append({'case_id':cid,'provider':provider,'model':MODELS[provider]['id'],'status':'recorded','analysis_card':final,'report_markdown':report,'program_decision':decision,'hard_failures':errors,'manual_review_flags':screen_report(report,payload['context'])})
    write_json(result_path,runs);summary(run_dir,cases,runs,budget,'running')
    print(json.dumps({'completed':len(runs),'of':30,'provider':provider,'case':cid,'cost_committed_usd':str(budget.committed())},ensure_ascii=False),flush=True)
    if errors and case['definition']['id']=='M01':raise StopPilot('Initial case failed; pause for inspection, no replacement')
  return summary(run_dir,cases,runs,budget,'complete')
 except (StopPilot,RequestFailure) as e:
  summary(run_dir,cases,runs,budget,'stopped_for_inspection')
  write_json(run_dir/'stop.json',{'reason':str(e),'no_automatic_extra_calls':True});raise

def run(run_dir,execute=False):
 run_dir=Path(run_dir);run_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
 # Lock before loading any ledger/state, including preparation and resume.
 with (run_dir/'.run.lock').open('a') as lock:
  try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise StopPilot('Another pilot process owns this run directory') from None
  return _run_locked(run_dir,execute)

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-dir',type=Path,default=DEFAULT_DIR);parser.add_argument('--execute',action='store_true');args=parser.parse_args()
 try:
  result=run(args.run_dir,args.execute)
  print(json.dumps({k:v for k,v in result.items() if k in ['status','missing','generation_calls','cost_committed_usd']},ensure_ascii=False));return 0
 except (StopPilot,RequestFailure) as e:
  print(json.dumps({'status':'stopped','reason':str(e)},ensure_ascii=False));return 2
 except (ValueError,KeyError,TypeError,ImportError,OSError) as e:
  print(json.dumps({'status':'stopped','error_type':type(e).__name__,'reason':'Local setup or response format needs inspection; no automatic repair request.'}));return 2

if __name__=='__main__':raise SystemExit(main())
