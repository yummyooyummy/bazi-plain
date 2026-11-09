#!/usr/bin/env python3
"""Build versioned lookup facts and an attributed offline GeoNames subset."""
import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

from lunar_python.EightChar import EightChar
from lunar_python.util import LunarUtil

DATA = Path(__file__).resolve().parent / 'data'


def build_tables():
    stems = '甲乙丙丁戊己庚辛壬癸'
    branches = '子丑寅卯辰巳午未申酉戌亥'
    data = {
        'schema_version': '0.1',
        'sources': [
            {'title': 'lunar-python 1.4.9 lookup tables', 'url': 'https://github.com/6tail/lunar-python', 'license': 'MIT'},
            {'title': '傳統干支關係（結構，不直接判吉凶）', 'url': 'https://zh.wikisource.org/wiki/三命通會'},
        ],
        'stems': list(stems), 'branches': list(branches),
        'stem_elements': LunarUtil.WU_XING_GAN,
        'branch_elements': dict(zip(branches, '水土木木土火火土金金土水')),
        'hidden_stems': LunarUtil.ZHI_HIDE_GAN,
        'ten_gods': LunarUtil.SHI_SHEN,
        'growth_stages': list(EightChar.CHANG_SHENG),
        'growth_offsets': EightChar._EightChar__CHANG_SHENG_OFFSET,
        'stem_combine': [['甲','己','土'],['乙','庚','金'],['丙','辛','水'],['丁','壬','木'],['戊','癸','火']],
        'stem_opposition': [['甲','庚'],['乙','辛'],['丙','壬'],['丁','癸']],
        'branch_combine': ['子丑','寅亥','卯戌','辰酉','巳申','午未'],
        'branch_clash': ['子午','丑未','寅申','卯酉','辰戌','巳亥'],
        'branch_harm': ['子未','丑午','寅巳','卯辰','申亥','酉戌'],
        'branch_break': ['子酉','丑辰','寅亥','卯午','巳申','未戌'],
        'punishment_groups': ['寅巳申','丑戌未'], 'mutual_punishment': ['子卯'],
        'self_punishment': list('辰午酉亥'),
        'triple_combine': [['申子辰','水'],['亥卯未','木'],['寅午戌','火'],['巳酉丑','金']],
        'triple_meeting': [['寅卯辰','木'],['巳午未','火'],['申酉戌','金'],['亥子丑','水']],
        'lu': dict(zip(stems, '寅卯巳午巳午申酉亥子')),
        'yang_blade': dict(zip('甲丙戊庚壬', '卯午午酉子')),
        'tianyi': {'甲':'丑未','戊':'丑未','庚':'丑未','乙':'子申','己':'子申','丙':'亥酉','丁':'亥酉','壬':'卯巳','癸':'卯巳','辛':'寅午'},
        'wenchang': dict(zip(stems,'巳午申酉申酉亥子寅卯')),
        'yima_by_day_branch': {b:y for group,y in [('申子辰','寅'),('寅午戌','申'),('巳酉丑','亥'),('亥卯未','巳')] for b in group},
        'notes': ['陰干羊刃未定，不輸出。', '天干合與三合三會只報結構；成立合化需另行判定。', '藏干按本氣等來源次序列示，不自行賦予力量百分比。'],
    }
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA/'tables.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')


def read_geonames(path):
    with zipfile.ZipFile(path) as z:
        # Country zips start with readme.txt; select the actual tab-separated data.
        filename = max((i for i in z.infolist() if i.filename.endswith('.txt') and i.filename.lower()!='readme.txt'),key=lambda i:i.file_size).filename
        for line in z.read(filename).decode('utf-8').splitlines():
            cols = line.split('\t')
            if len(cols) == 19:
                yield cols


def build_cities(cities_zip, china_zip=None):
    records = {}
    for c in read_geonames(cities_zip):
        # Chinese populated places, capitals, large overseas cities, and HK/MO/TW.
        if c[8] not in ['CN','HK','MO','TW'] and c[7] != 'PPLC' and int(c[14] or 0) < 500000:
            continue
        records[c[0]] = c
    admin = []
    if china_zip:
        for c in read_geonames(china_zip):
            if c[6] == 'A' and c[7] in ['ADM1','ADM2']:
                records[c[0]] = c
                if c[7] == 'ADM2': admin.append(c[0])
    result = []
    for ident,c in sorted(records.items(), key=lambda x:int(x[0])):
        aliases = [c[1],c[2]]
        aliases += [s for s in c[3].split(',') if re.fullmatch(r'[\u4e00-\u9fff]{2,12}',s)]
        result.append({'id':ident,'name':c[1],'aliases':list(dict.fromkeys(aliases)),
            'latitude':float(c[4]),'longitude':float(c[5]),'country':c[8],
            'feature':c[7],'admin1':c[10],'admin2':c[11],
            'population':int(c[14] or 0),'timezone':c[17],
            'source':f'https://www.geonames.org/{ident}/'})
    payload = {'schema_version':'0.1','source':'GeoNames','license':'CC-BY-4.0',
        'license_url':'https://creativecommons.org/licenses/by/4.0/',
        'readme':'https://download.geonames.org/export/dump/readme.txt','retrieved':'2026-11-09',
        'changes':'Selected records and Chinese aliases; renamed fields; no coordinate changes.',
        'source_sha256':{'cities15000.zip':hashlib.sha256(Path(cities_zip).read_bytes()).hexdigest()},
        'coverage':{'records':len(result),'china_adm2_records':len(admin),
            'note':'GeoNames行政記錄並非中國官方行政名錄逐項驗收；邊界盤需提供實際經度。'},
        'cities':result}
    if china_zip:payload['source_sha256']['CN.zip']=hashlib.sha256(Path(china_zip).read_bytes()).hexdigest()
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA/'cities.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(payload['coverage'],ensure_ascii=False))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cities-zip',type=Path)
    parser.add_argument('--china-zip',type=Path)
    args=parser.parse_args()
    build_tables()
    if args.cities_zip:build_cities(args.cities_zip,args.china_zip)
