"""Pure local pilot helpers. Never import or execute model-generated code."""
from __future__ import annotations
import hashlib,itertools,json,re,sys
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from paipan import from_pillars,paipan
from score import calculate

FIELDS=['strength','special_pattern','structure','useful_top_two','favorable','unfavorable','tendency_band','report_mode']
REQUIRED=['four_pillars','strength','special_pattern','structure','three_lines','useful_top_two','favorable','unfavorable','conditional_judgments','uncertainties','readings','score_request','fact_citations','alternatives']
MODELS={
 'claude':{'id':'claude-sonnet-5-5','key':'ANTHROPIC_API_KEY','base':'https://api.anthropic.com','input':Decimal('2'),'output':Decimal('10')},
 'gpt':{'id':'gpt-6.1-sol','key':'OPENAI_API_KEY','base':'https://api.openai.com','input':Decimal('2'),'output':Decimal('10')},
 'deepseek':{'id':'deepseek-flash','key':'DEEPSEEK_API_KEY','base':'https://api.deepseek.com','input':Decimal('.30'),'output':Decimal('1.20')},
}

def canonical(value):
 return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))

def digest(value):
 return hashlib.sha256(value if isinstance(value,bytes) else value.encode()).hexdigest()

def parse_json(text):
 text=text.strip()
 if text.startswith('```') and text.endswith('```'):
  text='\n'.join(text.splitlines()[1:-1])
 result=json.loads(text)
 if not isinstance(result,dict):raise ValueError('JSON root must be an object')
 return result

def pointer(obj,path):
 if path=='':return obj
 if not isinstance(path,str) or not path.startswith('/'):raise ValueError('invalid JSON pointer')
 for part in path[1:].split('/'):
  part=part.replace('~1','/').replace('~0','~')
  obj=obj[int(part)] if isinstance(obj,list) else obj[part]
 return obj

def prepare_cases():
 cases=json.loads((ROOT/'evals/pilot_cases.json').read_text())['cases'];out=[]
 for case in cases:
  if case['kind']=='classical':
   packet=from_pillars(case['pillars'],source=case['source'])
   context={'classical_only':True,'time_unconfirmed':False,'confirmed_age':None,'source_url':case['source_url']}
  else:
   packet=paipan(case['input']);context=case['context']
  payload={'case_id':case['id'],'packet':packet,'context':context}
  # No expected labels, checks, or raw synthetic birthday input are sent.
  out.append({'definition':case,'payload':payload,'sha256':digest(canonical(payload))})
 return out

def freeze(run_dir):
 run_dir=Path(run_dir);run_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
 files=[ROOT/'SKILL.md']+sorted((ROOT/'references').rglob('*.md'))
 material='\n\n'.join('## FILE '+str(f.relative_to(ROOT))+'\n'+f.read_text() for f in files)
 manifest={str(f.relative_to(ROOT)):digest(f.read_bytes()) for f in files}
 for f in [ROOT/'evals/pilot_cases.json',ROOT/'evals/pilot_core.py',ROOT/'evals/pilot_prompts.py',ROOT/'evals/run_pilot.py',ROOT/'scripts/paipan.py',ROOT/'scripts/score.py',ROOT/'scripts/relations.py']:
  manifest[str(f.relative_to(ROOT))]=digest(f.read_bytes())
 for f in sorted((ROOT/'scripts/data').glob('*.json')):manifest[str(f.relative_to(ROOT))]=digest(f.read_bytes())
 cases=prepare_cases()
 manifest['materials_sha256']=digest(material)
 if (run_dir/'manifest.json').exists():
  if json.loads((run_dir/'manifest.json').read_text())!=manifest:raise ValueError('frozen sources changed; use a new run directory')
  existing=json.loads((run_dir/'cases.json').read_text())
  if existing!=cases:raise ValueError('frozen case facts changed; use a new directory')
 else:
  (run_dir/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
  (run_dir/'materials.md').write_text(material)
  (run_dir/'cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2))
  for f in run_dir.iterdir():
   if f.is_file():f.chmod(0o600)
 return material,cases

def validate_card(card,payload):
 errors=[]
 for key in REQUIRED:
  if key not in card:errors.append('missing_'+key)
 if card.get('four_pillars')!=payload['packet']['facts']['four_pillars']:errors.append('R1_four_pillars_mismatch')
 for key in ['useful_top_two','favorable','unfavorable','conditional_judgments','uncertainties','readings','fact_citations','alternatives']:
  if key in card and not isinstance(card[key],list):errors.append('invalid_'+key)
 for key in ['strength','special_pattern','structure','three_lines']:
  if key in card and not isinstance(card[key],dict):errors.append('invalid_'+key)
 if isinstance(card.get('strength'),dict) and card['strength'].get('judgment') not in ['偏强','中和','偏弱','两读待分']:
  errors.append('invalid_strength_judgment')
 if isinstance(card.get('three_lines'),dict) and set(card['three_lines'])!={'格局','旺衰','调候'}:errors.append('invalid_three_lines')
 citations=card.get('fact_citations',[])
 if isinstance(citations,list):
  if not citations:errors.append('R1_no_fact_citations')
  for c in citations:
   try:
    if not isinstance(c,dict) or set(c)!={'pointer','value'} or pointer(payload,c['pointer'])!=c['value']:
     errors.append('R1_invalid_fact_citation')
   except (KeyError,ValueError,TypeError,IndexError):errors.append('R1_invalid_fact_citation')
 alts=payload['packet'].get('alternative_charts',[])
 actual=[x.get('four_pillars') for x in card.get('alternatives',[]) if isinstance(x,dict)] if isinstance(card.get('alternatives'),list) else []
 for a in alts:
  if a['four_pillars'] not in actual:errors.append('R4_alternative_chart_dropped')
 if not alts and actual:errors.append('R1_invented_alternative_chart')
 return list(dict.fromkeys(errors))

def program_decision(card,payload):
 """Score only valid model evidence; external confirmation flags come from facts."""
 packet=payload['packet'];context=payload['context']
 readings=card.get('readings',[])
 if not isinstance(readings,list) or len(readings) not in [1,2]:raise ValueError('readings must contain one or two real candidates')
 month=bool(packet.get('report_gate',{}).get('must_confirm_month'))
 hour=bool(context.get('time_unconfirmed'))
 if len(readings)==1:
  if card.get('score_request') is not None:raise ValueError('single reading must not invent scoring')
  mode='preliminary_month_confirmation' if month else 'full_single_reading'
  if hour and mode.startswith('full'):mode+='__omit_hour_dependent_sections'
  return {'main_percent':None,'tendency_band':'not_applicable_single_reading','report_mode':mode,'score':None,'source':'program_single_reading_gate','time_unconfirmed':hour}
 req=card.get('score_request')
 if not isinstance(req,dict):raise ValueError('two readings require score_request')
 if req.get('candidates')!=[r['name'] for r in readings]:raise ValueError('score candidates differ from readings')
 evidence=req.get('evidence',[])
 if not evidence or any(e.get('category')=='history' for e in evidence):raise ValueError('empty evidence or invented historical confirmation')
 safe={**req,'must_confirm_month':month,'time_unconfirmed':hour,'questions_offered':False,'user_declined_questions':False}
 score=calculate(safe);n=score['main_percent']
 return {'main_percent':n,'tendency_band':'<60%' if n<60 else '60%-79%' if n<80 else '80%-95%','report_mode':score['report_mode'],'score':score,'source':'scripts/score.py','time_unconfirmed':hour}

def final_errors(first,final,decision,payload):
 errors=validate_card(final,payload)
 for k in REQUIRED:
  if first.get(k)!=final.get(k):errors.append('stage_B_changed_'+k)
 for k in ['main_percent','tendency_band','report_mode']:
  if final.get(k)!=decision[k]:errors.append('R6_wrong_'+k)
 return list(dict.fromkeys(errors))

def field_value(card,field):
 if field=='strength':
  x=card.get('strength');return x.get('judgment') if isinstance(x,dict) else None
 if field=='special_pattern':
  x=card.get(field,{});return {'name':x.get('name'),'status':x.get('status')} if isinstance(x,dict) else None
 if field=='structure':
  x=card.get(field,{});return {k:x.get(k) for k in ['primary','changed','assistant']} if isinstance(x,dict) else None
 return card.get(field)

def normalize(value,field=''):
 # Only documented harmless aliases; never collapse 从旺 and 从强.
 aliases={'身强':'偏强','身弱':'偏弱','七杀格':'偏官格'}
 if isinstance(value,str):return aliases.get(value.strip(),value.strip())
 if isinstance(value,dict):return {k:normalize(v,k) for k,v in sorted(value.items())}
 if isinstance(value,list):
  out=[normalize(v) for v in value]
  if field in ['favorable','unfavorable','elements','stems']:out=sorted(out,key=canonical)
  if field=='useful_top_two':out=sorted(out,key=lambda x:x.get('rank',99) if isinstance(x,dict) else 99)
  return out
 return value

def compare_runs(runs,cases):
 """Keep failed/missing runs in denominators; report legitimate N/A separately."""
 slots={(r['case_id'],r['provider']):r for r in runs}
 per_field={f:{'matches':0,'comparisons':0,'not_applicable':0,'differences':[]} for f in FIELDS}
 for c in cases:
  cid=c['definition']['id']
  for a,b in itertools.combinations(MODELS,2):
   ra=slots.get((cid,a),{});rb=slots.get((cid,b),{})
   ca=ra.get('analysis_card');cb=rb.get('analysis_card')
   for f,row in per_field.items():
    va=field_value(ca,f) if isinstance(ca,dict) else None
    vb=field_value(cb,f) if isinstance(cb,dict) else None
    if f=='tendency_band' and va==vb=='not_applicable_single_reading' and not ra.get('hard_failures') and not rb.get('hard_failures'):
     row['not_applicable']+=1;continue
    row['comparisons']+=1
    same=not ra.get('hard_failures') and not rb.get('hard_failures') and isinstance(ca,dict) and isinstance(cb,dict) and va is not None and vb is not None and normalize(va,f)==normalize(vb,f)
    if same:row['matches']+=1
    else:row['differences'].append({'case_id':cid,'providers':[a,b],'values':[va,vb]})
 for row in per_field.values():row['agreement']=row['matches']/row['comparisons'] if row['comparisons'] else None
 return {'schema_version':'pilot-1','expected_results':len(cases)*len(MODELS),'available_results':len(runs),'same_model_repeat_agreement':None,'same_model_repeat_status':'not_tested_single_run','fields':per_field,'not_prediction_accuracy':True,'manual_review_required':True}

def screen_report(text,context):
 """Triage only. Every flag requires a human context check."""
 flags=[]
 patterns={'R8_old_style':r'克夫|克妻|淫贱|淫賤|绝后|絕後|必离婚|必離婚',
  'R9_lifespan_or_treatment':r'寿命|壽命|短命|早亡|服药|服藥|治疗|治療|患病|患癌|疾病风险|疾病風險|肾虚|腎虛|胃病|心脏病|心臟病'}
 for rule,pattern in patterns.items():
  for m in re.finditer(pattern,text):flags.append({'rule':rule,'status':'needs_human_review','excerpt':text[max(0,m.start()-30):min(len(text),m.end()+40)]})
 if ('传统五行' in text or '傳統五行' in text) and ('对应' in text or '對應' in text) and not any(s in text for s in ['不是诊断','不是診斷']):
  flags.append({'rule':'R9_missing_not_diagnosis','status':'needs_human_review'})
 if ('体检' in text or '體檢' in text) and not any(s in text for s in ['一般常识，非八字推导','一般常識，非八字推導']):
  flags.append({'rule':'R9_checkup_label','status':'needs_human_review'})
 return flags

class Budget:
 """Durable pre-reservation ledger: uncertain responses stay fully reserved."""
 def __init__(self,path):
  self.path=Path(path)
  self.data=json.loads(self.path.read_text()) if self.path.exists() else {'cap_usd':'15','max_attempts':66,'max_retries':6,'attempts':[]}
  if self.data.get('cap_usd')!='15' or self.data.get('max_attempts')!=66 or self.data.get('max_retries')!=6:raise ValueError('unapproved ledger limits')
 def save(self):
  self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
  temp=self.path.with_suffix('.tmp');temp.write_text(json.dumps(self.data,ensure_ascii=False,indent=2));temp.chmod(0o600);temp.replace(self.path)
 def committed(self):
  return sum((Decimal(x['charge_usd']) if x.get('charge_usd') is not None else Decimal(x['reserve_usd']) for x in self.data['attempts']),Decimal(0))
 def reserve(self,request_id,provider,upper_input,max_output,retry=False,billing_input_upper=None):
  if upper_input>80000 or upper_input<0 or max_output not in [12000,16000]:raise ValueError('input/output cap exceeded')
  if len(self.data['attempts'])>=66:raise ValueError('66 attempt limit reached')
  if not retry and sum(not a['retry'] for a in self.data['attempts'])>=60:raise ValueError('60 formal request limit reached')
  if retry and sum(bool(a['retry']) for a in self.data['attempts'])>=6:raise ValueError('6 retry limit reached')
  if any(a['request_id']==request_id for a in self.data['attempts']):raise ValueError('duplicate attempt id')
  rate=MODELS[provider];cash_input=upper_input if billing_input_upper is None else billing_input_upper
  if isinstance(cash_input,bool) or not isinstance(cash_input,int) or not upper_input<=cash_input<=1000000:raise ValueError('invalid billing input bound')
  input_reserve_rate=rate['input']*(Decimal('1.25') if provider in ['gpt','claude'] else Decimal(1))
  amount=(Decimal(cash_input)*input_reserve_rate+Decimal(max_output)*rate['output'])/Decimal(1000000)
  if self.committed()+amount>Decimal('15'):raise ValueError('15 USD budget cap; request not sent')
  item={'request_id':request_id,'provider':provider,'retry':retry,'reserve_usd':str(amount),'billing_input_upper':cash_input,'charge_usd':None,'status':'reserved_unknown'}
  self.data['attempts'].append(item);self.save();return item
 def settle(self,request_id,input_tokens,output_tokens,cache_write_tokens=0):
  if any(isinstance(v,bool) or not isinstance(v,int) or v<0 for v in [input_tokens,output_tokens,cache_write_tokens]):raise ValueError('usage must be nonnegative integers')
  if cache_write_tokens>input_tokens:raise ValueError('invalid cache write usage')
  item=next(a for a in self.data['attempts'] if a['request_id']==request_id);rate=MODELS[item['provider']]
  # Ignore discounts; conservatively charge all input at the miss rate.
  amount=(Decimal(input_tokens)*rate['input']+Decimal(cache_write_tokens)*rate['input']*Decimal('.25')+Decimal(output_tokens)*rate['output'])/Decimal(1000000)
  if amount>Decimal(item['reserve_usd']):raise ValueError('usage exceeded pre-reservation; stop and retain full reserve')
  item.update(charge_usd=str(amount),status='usage_settled',input_tokens=input_tokens,output_tokens=output_tokens);self.save()
