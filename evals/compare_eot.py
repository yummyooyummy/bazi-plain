from datetime import datetime
from math import pi,sin,cos
import calendar,astronomy,json,time
from pathlib import Path
errors={'noaa_fractional_year':[],'common_B_approximation':[]}
for year in range(1900,2101):
 for month in range(1,13):
  for day in [1,8,15,22]:
   d=datetime(year,month,day,12);t=astronomy.Time.Make(year,month,day,12,0,0)
   v=astronomy.RotateVector(astronomy.Rotation_EQJ_EQD(t),astronomy.GeoVector(astronomy.Body.Sun,t,True));ra=astronomy.EquatorFromVector(v).ra
   precise=(((astronomy.SiderealTime(t)-ra+12)%24-12+12)%24-12)*3600
   n=d.timetuple().tm_yday;gamma=2*pi/(366 if calendar.isleap(year) else 365)*(n-1)
   noaa=229.18*(.000075+.001868*cos(gamma)-.032077*sin(gamma)-.014615*cos(2*gamma)-.040849*sin(2*gamma))*60
   b=2*pi*(n-81)/364;common=(9.87*sin(2*b)-7.53*cos(b)-1.5*sin(b))*60
   errors['noaa_fractional_year'].append(abs(noaa-precise));errors['common_B_approximation'].append(abs(common-precise))
report={'sample_years':[1900,2100],'sample_days_each_month':[1,8,15,22],'samples_per_algorithm':len(errors['noaa_fractional_year']),'reference':'Astronomy Engine 2.1.19; geocentric apparent RA and GAST','not_a_proven_error_bound':True,'absolute_error_seconds':{k:{'max':round(max(v),3),'mean':round(sum(v)/len(v),3),'p95':round(sorted(v)[int(len(v)*.95)],3)} for k,v in errors.items()}}
print(json.dumps(report,ensure_ascii=False,indent=2))
