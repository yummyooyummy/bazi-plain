from lunar_python import Solar
from datetime import datetime,timezone,timedelta
import astronomy,json
from pathlib import Path
names={'立春':315,'惊蛰':345,'清明':15,'立夏':45,'芒种':75,'小暑':105,'立秋':135,'白露':165,'寒露':195,'立冬':225,'大雪':255,'小寒':285}
errors=[]
for y in range(1901,2100):
 table=Solar.fromYmdHms(y,7,1,12,0,0).getLunar().getJieQiTable()
 for name,s in table.items():
  if name not in names or s.getYear()!=y:continue
  bj=datetime.fromisoformat(s.toYmdHms()).replace(tzinfo=timezone(timedelta(hours=8)));u=bj.astimezone(timezone.utc)
  before=u-timedelta(days=2);t=astronomy.Time.Make(before.year,before.month,before.day,before.hour,before.minute,before.second)
  found=astronomy.SearchSunLongitude(names[name],t,4)
  dt=found.Utc().replace(tzinfo=timezone.utc);errors.append(abs((dt-u).total_seconds()))
report={'sample_years':[1901,2099],'samples':len(errors),'max_difference_seconds':round(max(errors),3),'mean_difference_seconds':round(sum(errors)/len(errors),3),'p95_difference_seconds':round(sorted(errors)[int(.95*len(errors))],3),'not_absolute_accuracy_proof':True,'versions':{'lunar_python':'1.4.9','astronomy_engine':'2.1.19'}}
print(json.dumps(report,ensure_ascii=False,indent=2))
