#!/usr/bin/env python3
"""Offline BaZi facts: UTC for Jie, apparent solar clock for day/hour.

Read one JSON request from stdin or --input (outside a public repository).
Default evidence omits the original birthday; --audit is for local diagnosis.
"""
from __future__ import annotations

import argparse
import calendar
import json
import math
import re
import sys
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from importlib import metadata
from pathlib import Path
from zoneinfo import ZoneInfo

import astronomy
import tzdata
from lunar_python import Lunar, LunarMonth, Solar

from relations import TABLES, STEMS, BRANCHES, analyze, growth, ten_god, void_branches

UTC = timezone.utc
BJ = timezone(timedelta(hours=8))
DATA = Path(__file__).resolve().parent/'data'
JIE_LONGITUDE = dict(zip(['小寒','立春','惊蛰','清明','立夏','芒种','小暑','立秋','白露','寒露','立冬','大雪'],[285,315,345,15,45,75,105,135,165,195,225,255]))


class InputError(ValueError):
    pass


@lru_cache(maxsize=256)
def get_zone(key):
    if not isinstance(key,str) or key.startswith('/') or any(p in ['', '.', '..'] for p in key.split('/')):
        raise InputError('需要有效的 IANA 時區名稱')
    path=Path(tzdata.__file__).parent/'zoneinfo'/key
    try:
        with path.open('rb') as stream:return ZoneInfo.from_file(stream,key=key)
    except (OSError,ValueError):raise InputError('時區不在已鎖定的 tzdata 資料庫中')


def resolve_local(naive, zone_name, fold=None):
    zone=get_zone(zone_name);possible={}
    for f in [0,1]:
        aware=naive.replace(tzinfo=zone,fold=f)
        instant=aware.astimezone(UTC)
        if instant.astimezone(zone).replace(tzinfo=None)==naive:possible[f]=instant
    if not possible:raise InputError('這個當地時間因夏令時跳時而不存在；請核對出生記錄')
    if len(set(possible.values()))>1:
        if fold not in [0,1]:raise InputError('這個當地時間因回撥出現兩次；請確認 fold=0（較早）或 fold=1（較晚）')
        return possible[fold]
    if fold not in [None,0,1]:raise InputError('fold 只能是0或1')
    return next(iter(possible.values()))


@lru_cache(maxsize=1)
def city_database():
    return json.loads((DATA/'cities.json').read_text())


def resolve_location(request):
    city=request.get('city');ident=request.get('city_id');matches=[]
    def city_key(s):
        if not isinstance(s,str):return s
        for tail in ['市','地区']:
            if s.endswith(tail) and len(s)>len(tail)+1:return s[:-len(tail)]
        return s
    if city or ident:
        for row in city_database()['cities']:
            if (ident and row['id']==str(ident)) or (not ident and any(city_key(city)==city_key(a) for a in row['aliases'])):matches.append(row)
        # Administrative entities and their capital settlement may share the same name.
        populated=[r for r in matches if r['feature'].startswith('PPL')]
        if populated:matches=populated
        if not matches and not ('longitude' in request and request.get('timezone')):raise InputError('離線城市表未找到地點；請提供 longitude 和 timezone，或使用 city_id')
        if len(matches)>1:
            labels=', '.join(f"{r['name']}({r['id']}, {r['country']}, {r['admin1']})" for r in matches[:8])
            raise InputError('地名有歧義，請用city_id選定：'+labels)
    row=matches[0] if matches else None
    if row and row['feature']=='ADM1':raise InputError('省级地名太宽；请提供具体城市，或明确经度与时区')
    lon=request.get('longitude',row['longitude'] if row else None)
    if isinstance(lon,bool) or not isinstance(lon,(int,float)) or not math.isfinite(lon) or not -180<=lon<=180:
        raise InputError('需要東經為正、西經為負且介於-180和180的經度')
    zone=request.get('timezone')
    if not zone:
        if not row:raise InputError('提供經度時也必須提供出生地IANA時區')
        if row['country']=='CN' and (row['timezone']=='Asia/Urumqi' or row['admin1']=='13'):
            raise InputError('新疆地點需先確認鐘表是北京時間還是新疆時間；請明確提供timezone')
        zone='Asia/Shanghai' if row['country']=='CN' else row['timezone']
    get_zone(zone)
    return {'longitude':float(lon),'timezone':zone,'city_id':row['id'] if row else None,
            'source':row['source'] if row else 'user_provided',
            'coordinate_quality':'user_provided' if 'longitude' in request else 'city_representative_point'}


def astro_time(utc):
    u=utc.astimezone(UTC)
    return astronomy.Time.Make(u.year,u.month,u.day,u.hour,u.minute,u.second+u.microsecond/1e6)


def equation_of_time_seconds(utc):
    """Apparent minus mean solar time, geocentric, UTC approximately UT1."""
    t=astro_time(utc)
    v=astronomy.RotateVector(astronomy.Rotation_EQJ_EQD(t),astronomy.GeoVector(astronomy.Body.Sun,t,True))
    ra=astronomy.EquatorFromVector(v).ra
    apparent=(astronomy.SiderealTime(t)-ra+12)%24
    u=utc.astimezone(UTC)
    hour=u.hour+u.minute/60+(u.second+u.microsecond/1e6)/3600
    return ((apparent-hour+12)%24-12)*3600


def clock_at(utc, location, mode='true_solar'):
    if mode=='civil':return utc.astimezone(get_zone(location['timezone'])).replace(tzinfo=None)
    if mode!='true_solar':raise InputError('clock_mode 只能是 true_solar 或 civil')
    return utc.astimezone(UTC).replace(tzinfo=None)+timedelta(seconds=location['longitude']*240+equation_of_time_seconds(utc))


def solar_from_datetime(d):
    return Solar.fromYmdHms(d.year,d.month,d.day,d.hour,d.minute,d.second)


def datetime_from_solar(s):
    return datetime.fromisoformat(s.toYmdHms())


def independent_day_pillar(d, zi_method):
    used=d.date()+timedelta(days=1 if zi_method=='23' and d.hour>=23 else 0)
    index=(used.toordinal()+1721425+49)%60
    return STEMS[index%10]+BRANCHES[index%12]


def pillar_details(pillars):
    if len(pillars)!=4:raise InputError('需要按年月日时提供四柱')
    from relations import validate_pillar
    for pillar in pillars:validate_pillar(pillar)
    day= pillars[2][0];day_void=void_branches(pillars[2]);result=[]
    for position,p in zip(['年','月','日','时'],pillars):
        hidden=[{'stem':g,'element':TABLES['stem_elements'][g],'ten_god':ten_god(day,g),
                 'own_growth_in_branch':growth(g,p[1])} for g in TABLES['hidden_stems'][p[1]]]
        result.append({'position':position,'ganzhi':p,'stem_element':TABLES['stem_elements'][p[0]],
            'branch_element':TABLES['branch_elements'][p[1]],'stem_ten_god':ten_god(day,p[0]),
            'hidden_stems':hidden,'growth_against_day_master':growth(day,p[1]),
            'in_day_void':p[1] in day_void,'own_xunkong':void_branches(p)})
    visible={el:sum(TABLES['stem_elements'][p[0]]==el for p in pillars)+sum(TABLES['branch_elements'][p[1]]==el for p in pillars) for el in '木火土金水'}
    support=[];wealth_officer=[]
    for item in result:
        if item['position']!='日':
            if item['stem_ten_god'] in ['比肩','劫财','正印','偏印']:support.append({'position':item['position'],'layer':'明干','stem':item['ganzhi'][0],'ten_god':item['stem_ten_god']})
            if item['stem_ten_god'] in ['正财','偏财','正官','七杀']:wealth_officer.append({'position':item['position'],'layer':'明干','stem':item['ganzhi'][0],'ten_god':item['stem_ten_god']})
        for h in item['hidden_stems']:
            entry={'position':item['position'],'layer':'藏干','stem':h['stem'],'ten_god':h['ten_god']}
            if h['ten_god'] in ['比肩','劫财','正印','偏印']:support.append(entry)
            if h['ten_god'] in ['正财','偏财','正官','七杀']:wealth_officer.append(entry)
    return {'day_master':day,'pillars':result,'day_void_branches':day_void,
            'visible_element_counts':visible,'counts_are_not_strength_weights':True,
            'pattern_observations':{'support_stems_including_hidden':support,
                'wealth_officer_stems_including_hidden':wealth_officer,
                'same_element_hidden_positions':[i['position'] for i in result if any(h['ten_god'] in ['比肩','劫财'] for h in i['hidden_stems'])],
                'note':'仅报告存在与否；藏而有气、是否得令有力、是否从格不能由字数决定。'},
            'relations':analyze(dict(zip(['年','月','日','时'],pillars)))}


def chart_core(utc, location, sex, mode, zi_method):
    civil_bj=utc.astimezone(BJ).replace(tzinfo=None)
    clock=clock_at(utc,location,mode)
    physical_ec=solar_from_datetime(civil_bj).getLunar().getEightChar()
    solar_ec=solar_from_datetime(clock).getLunar().getEightChar()
    solar_ec.setSect(2 if zi_method=='split' else 1)
    pillars=[physical_ec.getYear(),physical_ec.getMonth(),solar_ec.getDay(),solar_ec.getTime()]
    if pillars[2]!=independent_day_pillar(clock,zi_method):raise RuntimeError('日柱獨立校驗不一致，停止輸出')
    facts=pillar_details(pillars)
    facts['four_pillars']=pillars
    facts['day_independent_check']='passed'
    return facts,physical_ec,clock


def transit_facts(pillar, natal):
    day=natal[2][0]
    return {'stem_ten_god':ten_god(day,pillar[0]),'growth_against_day_master':growth(day,pillar[1]),
        'hidden_stems':[{'stem':g,'ten_god':ten_god(day,g),'element':TABLES['stem_elements'][g]} for g in TABLES['hidden_stems'][pillar[1]]],
        'own_xunkong':void_branches(pillar),'in_day_void':pillar[1] in void_branches(natal[2])}


def luck_data(ec, sex, zone_name, natal):
    yun=ec.getYun(1 if sex=='male' else 0,2)
    start=yun.getStartSolar()
    start_bj=datetime_from_solar(start).replace(tzinfo=BJ)
    steps=[]
    for n,dy in enumerate(yun.getDaYun(9)[1:]):
        s=start.nextYear(n*10);e=start.nextYear((n+1)*10)
        gz=dy.getGanZhi()
        steps.append({'index':n+1,'ganzhi':gz,'facts':transit_facts(gz,natal),
            'relations_to_natal':analyze({**dict(zip(['年','月','日','时'],natal)),'大运':gz}),
            'start':datetime_from_solar(s).replace(tzinfo=BJ).astimezone(get_zone(zone_name)).isoformat(),
            'end_exclusive':datetime_from_solar(e).replace(tzinfo=BJ).astimezone(get_zone(zone_name)).isoformat(),
            'start_age_years':yun.getStartYear()+n*10,'start_age_months':yun.getStartMonth(),
            'age_basis':'起运折算足年足月，不是虚岁'})
    return {'direction':'forward' if yun.isForward() else 'backward','method':'lunar-python Yun sect=2，按分钟折算三天一岁',
        'age':{'years':yun.getStartYear(),'months':yun.getStartMonth(),'days':yun.getStartDay(),'hours':yun.getStartHour()},
        'start':start_bj.astimezone(get_zone(zone_name)).isoformat(),'steps':steps}


def jie_event(jie):
    s=jie.getSolar();name=jie.getName()
    return {'kind':'jie','name':name,'utc':datetime_from_solar(s).replace(tzinfo=BJ).astimezone(UTC)}


def nearby_boundaries(utc, location, mode, uncertainty_minutes=0):
    clock=clock_at(utc,location,mode);events=[]
    limit=max(1800,uncertainty_minutes*60)
    for offset in [-1,0,1]:
        day=clock.date()+timedelta(days=offset)
        for hour in [0]+list(range(1,24,2)):
            target=datetime.combine(day,datetime.min.time()).replace(hour=hour)
            guess=utc+timedelta(seconds=(target-clock).total_seconds())
            for _ in range(4):guess+=target-clock_at(guess,location,mode)
            if abs((clock_at(guess,location,mode)-target).total_seconds())>.01:continue
            if abs((guess-utc).total_seconds())<=limit+.001:
                events.append({'kind':'day_boundary' if hour==0 else 'hour_boundary','name':target.strftime('%H:%M:%S'),'utc':guess})
    l=solar_from_datetime(utc.astimezone(BJ).replace(tzinfo=None)).getLunar()
    for jie in [l.getPrevJie(),l.getNextJie()]:
        event=jie_event(jie)
        if abs((event['utc']-utc).total_seconds())<=limit+.001:events.append(event)
    return sorted(events,key=lambda x:x['utc'])


def jie_crosscheck(event):
    if event['name'] not in JIE_LONGITUDE:return None
    start=event['utc']-timedelta(days=2)
    t=astronomy.SearchSunLongitude(JIE_LONGITUDE[event['name']],astro_time(start),4)
    if t is None:raise RuntimeError('獨立節氣核對未找到根')
    found=t.Utc().replace(tzinfo=UTC)
    return {'independent_utc':found.isoformat(),'difference_seconds':round((found-event['utc']).total_seconds(),3)}


@lru_cache(maxsize=256)
def annual_start(year):
    s=Solar.fromYmdHms(year,7,1,12,0,0).getLunar().getJieQiTable()['立春']
    return datetime_from_solar(s).replace(tzinfo=BJ).astimezone(UTC)


def annual_facts(start_year,end_year,natal,luck):
    if end_year-start_year>100 or start_year<1901 or end_year>2199:raise InputError('流年区间须在1901—2199且不超过101年')
    rows=[]
    for y in range(start_year,end_year+1):
        g=STEMS[(y-4)%10]+BRANCHES[(y-4)%12];begin=annual_start(y);end=annual_start(y+1)
        overlaps=[]
        for step in luck['steps']:
            a=datetime.fromisoformat(step['start']).astimezone(UTC);b=datetime.fromisoformat(step['end_exclusive']).astimezone(UTC)
            if a<end and b>begin:
                combined={**dict(zip(['年','月','日','时'],natal)),'大运':step['ganzhi'],'流年':g}
                overlaps.append({'luck':step['ganzhi'],'start_utc':max(a,begin).isoformat(),'end_utc_exclusive':min(b,end).isoformat(),
                    'relations_natal_luck_year':analyze(combined),
                    'relations_luck_year':analyze({'大运':step['ganzhi'],'流年':g})})
        rows.append({'year':y,'ganzhi':g,'start_utc':begin.isoformat(),'end_utc_exclusive':end.isoformat(),
            'facts':transit_facts(g,natal),
            'relations_to_natal':analyze({**dict(zip(['年','月','日','时'],natal)),'流年':g}),
            'luck_segments':overlaps,
            'ten_god':ten_god(natal[2][0],g[0]),'growth':growth(natal[2][0],g[1]),
            'in_day_void':g[1] in void_branches(natal[2])})
    return rows


def paipan(request):
    if not isinstance(request,dict):raise InputError('输入必须是JSON对象')
    if not isinstance(request.get('sex'),str):raise InputError('需要确认排大运所用性别参数')
    sex={'男':'male','女':'female','male':'male','female':'female'}.get(request.get('sex'))
    if not sex:raise InputError('排大运需要确认传统算法所用性别参数：male/female；不推断性别')
    location=resolve_location(request)
    mode=request.get('clock_mode','true_solar');zi=request.get('zi_method','split')
    if zi not in ['split','23']:raise InputError('zi_method只能是split（晚子日不换、时干借次日）或23（23点换日）')
    calendar_type=request.get('calendar','solar')
    try:
        raw=request['date'];raw_time=request['time']
        if not isinstance(raw,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',raw):raise InputError('日期格式须为YYYY-MM-DD')
        if not isinstance(raw_time,str) or not re.fullmatch(r'\d{2}:\d{2}(:\d{2}(\.\d{1,6})?)?',raw_time):raise InputError('时间格式须为HH:MM或HH:MM:SS，不能猜时辰')
        if calendar_type=='lunar':
            if not isinstance(request.get('is_leap_month'),bool):raise InputError('农历输入必须明确布尔值is_leap_month，不能猜闰月')
            ly,lm,ld=map(int,raw.split('-'))
            if not 1901<=ly<=2099:raise InputError('v0.1农历年份支持1901—2099')
            lm=-lm if request['is_leap_month'] else lm
            m=LunarMonth.fromYm(ly,lm)
            if m is None or not 1<=ld<=m.getDayCount():raise InputError('该农历月份或日数不存在，请核对闰月')
            s=Lunar.fromYmdHms(ly,lm,ld,0,0,0).getSolar()
            raw_date=datetime_from_solar(s).date()
        elif calendar_type=='solar':raw_date=date.fromisoformat(raw)
        else:raise InputError('calendar只能是solar或lunar')
        naive=datetime.fromisoformat(raw_date.isoformat()+'T'+raw_time)
    except (KeyError,TypeError,ValueError) as e:
        if isinstance(e,InputError):raise
        raise InputError('需要有效的日期YYYY-MM-DD及时间HH:MM[:SS]')
    if naive.tzinfo is not None:raise InputError('time不附UTC偏移；请用timezone与必要时的fold明确历史时区')
    if not 1901<=naive.year<=2099:raise InputError('v0.1出生日期支持1901—2099；区间外不保证历法口径')
    utc=resolve_local(naive,location['timezone'],request.get('fold'))
    uncertainty=request.get('time_uncertainty_minutes',0)
    if isinstance(uncertainty,bool) or not isinstance(uncertainty,(int,float)) or not math.isfinite(uncertainty) or not 0<=uncertainty<=1440:
        raise InputError('时间不确定范围须为0—1440分钟；未知时辰不能编造一个时间')
    facts,ec,clock=chart_core(utc,location,sex,mode,zi)
    luck=luck_data(ec,sex,location['timezone'],facts['four_pillars'])
    warnings=[];alternatives=[];bounds=[];seen={tuple(facts['four_pillars'])}
    for event in nearby_boundaries(utc,location,mode,uncertainty):
        row={'kind':event['kind'],'name':event['name'],'distance_seconds':round(abs((event['utc']-utc).total_seconds()),3),
             'civil_boundary_time':event['utc'].astimezone(get_zone(location['timezone'])).strftime('%H:%M:%S'),
             'civil_boundary_day_offset':(event['utc'].astimezone(get_zone(location['timezone'])).date()-naive.date()).days}
        if event['kind']=='jie':row['crosscheck']=jie_crosscheck(event)
        bounds.append(row)
        for side in [-1,1]:
            sample=event['utc']+timedelta(seconds=side)
            alt,aec,aclock=chart_core(sample,location,sex,mode,zi)
            if tuple(alt['four_pillars']) not in seen:
                seen.add(tuple(alt['four_pillars']))
                alternatives.append({'reason':event['kind'],'side':'before' if side<0 else 'after',
                    'zi_method':zi,'clock_mode':mode,
                    'four_pillars':alt['four_pillars'],'facts':alt,'luck':luck_data(aec,sex,location['timezone'],alt['four_pillars'])})
    # A late-Zi convention comparison uses the SAME physical birth instant.
    # An adjacent-midnight sample may have the same pillars but a different Yun start.
    late_zi=clock.hour==23
    zi_comparison=[]
    if late_zi:
        other_zi='23' if zi=='split' else 'split'
        alt,aec,_=chart_core(utc,location,sex,mode,other_zi)
        equivalent=[a for a in alternatives if a['four_pillars']==alt['four_pillars']]
        alternatives=[a for a in alternatives if a['four_pillars']!=alt['four_pillars']]
        alternatives.append({'reason':'late_zi_convention','side':'same_instant',
            'zi_method':other_zi,'clock_mode':mode,'same_birth_instant':True,
            'also_nearby_reasons':sorted({a['reason'] for a in equivalent}),
            'four_pillars':alt['four_pillars'],'facts':alt,
            'luck':luck_data(aec,sex,location['timezone'],alt['four_pillars'])})
        zi_comparison=[{'zi_method':method,'four_pillars':f['four_pillars'],'day_pillar':f['four_pillars'][2],
                        'hour_pillar':f['four_pillars'][3]} for method,f in [(zi,facts),(other_zi,alt)]]
        warnings.append('所用排盘钟面落在23:00—24:00晚子时；必须并列split早晚子与23点换日两盘，先用性格与已知经历校准，不得只给默认口径。')
    if bounds:warnings.append('距时辰、日界或节交接不超过30分钟（或所给不确定范围）；已列程序计算的相邻盘，须核对出生记录。')
    if location['coordinate_quality']=='city_representative_point':warnings.append('城市坐标是代表点，不是医院坐标；临界时应补实际经度。')
    try:asof=date.fromisoformat(request.get('as_of',datetime.now(get_zone('Asia/Shanghai')).date().isoformat()))
    except (ValueError,TypeError):raise InputError('as_of须为有效的YYYY-MM-DD')
    year0=request.get('year_start',asof.year);year1=request.get('year_end',year0+7)
    if isinstance(year0,bool) or isinstance(year1,bool) or not isinstance(year0,int) or not isinstance(year1,int) or year0>year1:raise InputError('流年起止年份须为递增整数')
    civil=utc.astimezone(get_zone(location['timezone']));eot=equation_of_time_seconds(utc)
    reference=datetime.combine(asof,datetime.min.time()).replace(tzinfo=get_zone('Asia/Shanghai')).astimezone(UTC)
    current=[s['ganzhi'] for s in luck['steps'] if datetime.fromisoformat(s['start'])<=reference<datetime.fromisoformat(s['end_exclusive'])]
    result={'schema_version':'0.1','status':'needs_confirmation' if alternatives or uncertainty else 'calculated',
        'versions':{p:metadata.version(p) for p in ['lunar-python','astronomy-engine','tzdata']},
        'conventions':{'clock_mode':mode,'zi_method':zi,'year_boundary':'立春真实时刻','month_boundary':'十二节真实时刻',
            'late_zi_policy':'compare_split_and_23_at_same_instant',
            'luck_age':'足年足月；Yun sect=2','eot':'geocentric apparent RA and GAST; UTC approximates UT1'},
        'location':location,'sex_parameter':sex,
        'clock':{'calculation_time':clock.strftime('%H:%M:%S.%f'),'day_offset_from_civil':(clock.date()-naive.date()).days,
            'equation_of_time_seconds':round(eot,3),'longitude_correction_from_utc_seconds':location['longitude']*240,
            'utc_offset_seconds':civil.utcoffset().total_seconds(),'dst_seconds':civil.dst().total_seconds(),
            'correction_from_civil_seconds':round((clock-naive).total_seconds(),3)},
        'facts':facts,'luck':luck,'current_luck_at_reference':{'as_of':asof.isoformat(),'reference':'指定日北京时间00:00','ganzhi':current[0] if current else None},
        'boundaries':bounds,'alternative_charts':alternatives,'warnings':warnings,
        'day_convention_comparison':{'required':late_zi,'same_birth_instant':True,'charts':zi_comparison},
        'report_gate':{'must_confirm_month':any(b['kind']=='jie' for b in bounds),'must_confirm_time':bool(uncertainty),
                       'must_confirm_zi_method':late_zi,
                       'interpretation_score_not_computed_by_calendar':True},
        'annual':annual_facts(year0,year1,facts['four_pillars'],luck),
        'privacy':{'raw_birth_date_included':False,'local_calculation_only':True,
                   'note':'四柱仍是个人资料；证据包不是不可逆匿名数据。'},
    }
    for alt in alternatives:
        if alt['reason']=='late_zi_convention':
            alt['annual']=annual_facts(year0,year1,alt['four_pillars'],alt['luck'])
            active=[s['ganzhi'] for s in alt['luck']['steps'] if datetime.fromisoformat(s['start'])<=reference<datetime.fromisoformat(s['end_exclusive'])]
            alt['current_luck_at_reference']={'as_of':asof.isoformat(),'reference':'指定日北京时间00:00','ganzhi':active[0] if active else None}
    if request.get('audit'):
        result['local_audit']={'civil':civil.isoformat(),'utc':utc.isoformat(),'calculation_clock':clock.isoformat()}
        result['privacy']['raw_birth_date_included']=True
    return result


def from_pillars(pillars, source='user_confirmed_or_classical'):
    if len(pillars)!=4:raise InputError('四柱模式需要按年月日时提供四柱')
    # pillar_details validates through relations; no invented birth date or luck epochs.
    facts=pillar_details(pillars);facts['four_pillars']=list(pillars)
    return {'schema_version':'0.1','status':'facts_only','source':source,'facts':facts,
        'luck':None,'annual':[],'boundaries':[],'alternative_charts':[],
        'warnings':['仅有四柱，未核验出生排盘；不能反推生日、起运和历年交运时刻。'],
        'report_gate':{'missing_calendar_evidence':True},
        'privacy':{'raw_birth_date_included':False,'local_calculation_only':True}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--input',type=Path,help='本地JSON输入；省略时从stdin读取')
    group.add_argument('--chart',nargs=4,metavar=('年柱','月柱','日柱','时柱'),help='仅有四柱的古籍或用户确认盘：不反推生日或大运')
    parser.add_argument('--audit',action='store_true',help='仅本地调试：证据包包含原始日期，不得提交仓库')
    args=parser.parse_args()
    try:
        if args.chart:
            print(json.dumps(from_pillars(args.chart),ensure_ascii=False,indent=2));return 0
        req=json.loads(args.input.read_text() if args.input else sys.stdin.read())
        if not isinstance(req,dict):raise InputError('输入必须是JSON对象')
        if args.audit:req['audit']=True
        print(json.dumps(paipan(req),ensure_ascii=False,indent=2));return 0
    except (InputError,ValueError,OSError) as e:
        print(json.dumps({'status':'input_required','message':str(e)},ensure_ascii=False));return 2


if __name__=='__main__':raise SystemExit(main())
