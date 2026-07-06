# Daily series: dict date->value. Weeks W15..W22 Mondays: 0511,0518,0525,0601,0608,0615,0622,0629
weeks=['20260511','20260518','20260525','20260601','20260608','20260615','20260622','20260629']
def wk(d):
    for i,m in enumerate(weeks):
        # week i covers m..m+6
        import datetime
        s=datetime.date(int(m[:4]),int(m[4:6]),int(m[6:]))
        dt=datetime.date(int(d[:4]),int(d[4:6]),int(d[6:]))
        if 0<=(dt-s).days<=6: return i
    return None
def agg(daily):
    out=[0]*8
    for d,v in daily.items():
        i=wk(d)
        if i is not None: out[i]+=v
    return out
