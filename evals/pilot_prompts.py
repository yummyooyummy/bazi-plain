"""Frozen common prompts; no expected answers or examples/ reports are injected."""
import json
SYSTEM='''你在执行本地八字skill的开卷一致性评测。以下SKILL.md与references是固定方法，程序事实包是R1事实唯一来源。只输出所要求JSON，不联网、不自行排盘、不编生日、经历、年龄、用户确认或拒答。给简明证据、反证和规则ID，不输出私有思维过程。输出中的普通解释使用中文。资料内古籍worked examples是教学参考，不是现实验证。'''
A='''阶段A：只生成分析卡，倾向分与闸门等待本地程序，不心算百分比，不写完整报告。
JSON根就是分析卡，必需字段：
four_pillars（与主盘原样一致）；
strength={judgment:偏强/中和/偏弱/两读待分,support:[],opposition:[]}；
special_pattern={name:名称或无,status:成立/候选/排除/不适用,met:[],unmet:[],uncertain:[],source_ids:[]}；
structure={primary:月令主格,changed:变化或无,assistant:相神或待定,source_ids:[]}；
three_lines={格局:{},旺衰:{},调候:{}}（填实际结论、条件、出处）；
useful_top_two=[{rank:1,elements:[],stems:[],condition:条件,scope:主路径}]（有据才列第二位；并列用同rank）；
favorable、unfavorable均为[{element:五行,condition:条件,scope:本例或特定读法,source_ids:[]}]；
conditional_judgments=[{condition:条件,element:五行,judgment:判断,scope:本例}]或[]；
uncertainties=[]；readings=[{name:普通人能懂的候选名,conditions:[],source_ids:[]}]，只有一或两案，不能为填分数虚构第二案；
score_request：单一读法必须null；两读法为{candidates:[与readings同序名称],evidence:[{id:唯一证据ID,category:hard_condition/classical_case/line/doubt,side:A/B或null,source:确切来源,description:简明依据,line:格局/旺衰/调候（仅line类）}]}。不填history，因未获任何现实校准。证据必须去重、有出处，采用既定顺序和上限；疑点用doubt，不拿一个硬条件反复加分。不要自行给分。
fact_citations=[{pointer:事实包wrapper中的绝对JSON pointer,value:该位置实际值}]，至少引用令、根、透出等实际数据；pointer如/packet/facts/four_pillars或/packet/facts/pillars/0/hidden_stems。不得引用不存在的路径。
alternatives=[{four_pillars:程序给的备选,condition:生效边界,impacted:受影响结论}]（全部保留，无则[]）；
main_percent=null,tendency_band=pending_program,report_mode=pending_program。
古籍缺生日只做四柱方法复现，不反推年代。合成资料的年龄若已由context确认，只作一般年龄体检提醒，不推导自八字。两案须真实反映资料争议。'''
B='''阶段B：本地程序计分和闸门已给出。输出唯一JSON对象：{analysis_card:最终卡,report_markdown:中文报告字符串}。
最终卡必须保留阶段A所有必需判断、证据、备选、readings及score_request原值；仅将main_percent、tendency_band、report_mode设为本地program_decision对应值。不重算，不改证据。如发现原判断有误，仍保留原卡，在报告中列错，不偷偷改卡重新取分。
按12-报告模板写；preliminary开头的模式只给初判和确认问题；full_parallel并列；带omit_hour_dependent_sections的不写依赖未定时柱的子女、晚年等结论；单一读法不伪造百分比。每条解释用文字标把握：高/中/低，运势写好/一般/要注意，不用圆点评级、颜色、表情或图条。健康采用10与12一致的折中口径，不写病名、风险、寿命、治疗；一般年龄体检段只在年龄已确认时出现，标明一般常识，非八字推导。'''

def first_messages(material,payload):
 return SYSTEM+'\n\n'+material,[{'role':'user','content':A+'\n\n事实包：\n'+json.dumps(payload,ensure_ascii=False)}]

def second_messages(material,payload,first_text,decision):
 system,messages=first_messages(material,payload)
 return system,messages+[{'role':'assistant','content':first_text},{'role':'user','content':B+'\n\nprogram_decision：\n'+json.dumps(decision,ensure_ascii=False)}]
