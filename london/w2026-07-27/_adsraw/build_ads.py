import json, re
BASE="/sessions/youthful-gifted-hypatia/mnt/Hong Kong/site/london/"
LP=json.load(open(BASE+"w2026-07-20/_ads_payload.json"))["data"]
OUT=BASE+"w2026-07-27/_ads_payload.json"
VEN=["Aqua Shard","Hutong","Regent St","Azzurra","Shiro Sushi","DSL"]

def norm(n): return re.sub(r"\s+"," ",n).strip()

# ---------------- GA4 CUR ----------------
# web: totalUsers, sessions, screenPageViews, avgSessionDuration, engagementRate(0-1), newUsers
WEBC={
 "Aqua Shard":[25710,35713,100203,216.99385,0.46694481,20261],
 "Hutong":[14461,20710,57726,183.26717,0.52216321,11278],
 "Kyoto":[4032,5200,16070,190.73426,0.63038462,3432],
 "Nueva":[2127,2784,8817,184.79489,0.59410920,1792],
 "Azzurra":[1617,2012,5615,167.59882,0.57256461,1395],
 "Shiro Sushi":[1359,1898,5819,191.89009,0.64963119,1158],
 "DSL":[5479,7325,23804,178.99608,0.59412969,4454]}
CHS_C={  # channel sessions cur
 "Aqua Shard":{"Organic Search":8572,"Paid Search":7419,"Direct":7321,"Unassigned":6401,"Cross-network":4154,"Paid Social":3730,"Referral":3042,"AI Assistant":318,"Organic Social":302,"Email":97,"Paid Other":2},
 "Hutong":{"Paid Social":5361,"Organic Search":4414,"Direct":3911,"Paid Search":3215,"Unassigned":2374,"Referral":1535,"Cross-network":1058,"Organic Social":181,"AI Assistant":98,"Email":92,"Paid Other":88},
 "Kyoto":{"Organic Search":2016,"Direct":1345,"Paid Search":688,"Unassigned":479,"Paid Social":411,"Organic Social":203,"Cross-network":195,"AI Assistant":95,"Referral":74,"Email":73,"Paid Other":6},
 "Nueva":{"Organic Search":1103,"Direct":748,"Organic Social":251,"Unassigned":240,"Cross-network":205,"Referral":162,"Paid Social":122,"Paid Search":66,"AI Assistant":29,"Email":2},
 "Azzurra":{"Direct":530,"Organic Search":461,"Paid Search":287,"Cross-network":227,"Paid Social":198,"Unassigned":198,"Email":103,"Referral":69,"Organic Social":38,"AI Assistant":23,"Paid Other":2},
 "Shiro Sushi":{"Organic Search":729,"Direct":486,"Paid Search":274,"Paid Social":196,"Referral":75,"Unassigned":52,"Cross-network":40,"Organic Social":33,"Email":7,"AI Assistant":4,"Paid Other":3},
 "DSL":{"Organic Search":2019,"Paid Social":1515,"Referral":1487,"Direct":1286,"Unassigned":806,"Cross-network":417,"Organic Social":151,"Paid Search":126,"Email":60,"AI Assistant":22,"Paid Other":10}}
CHB_C={  # channel bookings cur
 "Aqua Shard":{"Direct":353,"Paid Search":286,"Organic Search":285,"Unassigned":268,"Referral":89,"Cross-network":82,"Paid Social":30,"AI Assistant":23,"Organic Social":6,"Email":1},
 "Hutong":{"Direct":194,"Organic Search":170,"Paid Search":161,"Unassigned":106,"Paid Social":75,"Referral":50,"Cross-network":23,"Organic Social":6,"Paid Other":3,"AI Assistant":2,"Email":2},
 "Kyoto":{"Direct":75,"Organic Search":72,"Paid Search":27,"Unassigned":14,"AI Assistant":3,"Organic Social":3,"Cross-network":2,"Paid Social":2,"Email":1,"Referral":1},
 "Nueva":{"Organic Search":28,"Direct":27,"Unassigned":11,"Cross-network":6,"Referral":5,"Organic Social":3,"AI Assistant":2},
 "Azzurra":{"Organic Search":24,"Direct":22,"Paid Search":13,"Cross-network":7,"Unassigned":6,"Paid Social":2,"Referral":2},
 "Shiro Sushi":{"Organic Search":46,"Direct":37,"Paid Search":30,"Unassigned":12,"Referral":10,"Cross-network":8,"AI Assistant":1},
 "DSL":{"Referral":178,"Organic Search":153,"Direct":80,"Unassigned":64,"Paid Social":23,"Paid Search":11,"Cross-network":7,"Organic Social":3,"Paid Other":3,"AI Assistant":1,"Email":1}}
DEVC={  # mobile,desktop,tablet cur
 "Aqua Shard":[28734,6622,427],"Hutong":[17712,3131,173],"Kyoto":[4060,1156,19],
 "Nueva":[2167,601,15],"Azzurra":[1448,555,14],"Shiro Sushi":[1358,530,9],"DSL":[6136,1096,55]}
LANDC={
 "Aqua Shard":[["/",13551,415],["/peter-pan-afternoon-tea",4581,85],["/menus",3004,25],["/2025/04/09/sunday-roast-london",2691,1],["/explore/aquashard/reservations/create/search",2311,277]],
 "Hutong":[["/",6173,200],["/menus",4015,37],["/menus/lunch-ppc",3287,33],["/explore/hutonglondon/reservations/create/search",2245,261],["/events/golden-sky-dinner-menu",961,14]],
 "Regent St":[["/ (Kyoto)",2144,56],["/ (Nueva)",1219,31],["/explore/aquakyoto/reservations/create/search (Kyoto)",733,66],["/bar (Kyoto)",423,9],["/explore/aquanueva/reservations/create/search (Nueva)",338,29]],
 "Azzurra":[["/",841,27],["/menus",216,5],["/events/oyster-hour",150,1],["/explore/azzurra/reservations/create/search",131,24],["/experiences/azzurra/bottomless-oysters-4817614535360512",110,2]],
 "Shiro Sushi":[["/",845,62],["/explore/shiro/reservations/create/search",205,58],["/menus",179,4],["/unlimited-sushi-brunch",151,0],["/explore/shiro/reservations/manage",91,9]],
 "DSL":[["/",2447,155],["/menus",1997,28],["/explore/dimsumlibrary/reservations/create/search",719,172],["/explore/dimsumlibrary/reservations/manage",550,47],["/menus/a-la-carte",387,5]]}
# ---------------- GA4 YOY ----------------
WEBY={"Aqua Shard":[33025,64069],"Hutong":[15282,29571],"Kyoto":[4368,5734],"Nueva":[3011,3974],
 "Azzurra":[2235,2710],"Shiro Sushi":[2265,2737],"DSL":[3721,4810]}
CHS_Y={
 "Aqua Shard":{"Paid Search":16673,"Organic Search":13361,"Direct":9466,"Referral":9393,"Paid Social":9226,"Cross-network":3932,"Unassigned":1718,"Organic Social":236,"Paid Other":52,"Email":21},
 "Hutong":{"Organic Search":6576,"Referral":5697,"Paid Social":5391,"Cross-network":4293,"Direct":3284,"Paid Search":2867,"Email":694,"Unassigned":403,"Organic Social":197,"Paid Other":104,"Organic Video":1},
 "Kyoto":{"Organic Search":2716,"Direct":1080,"Paid Search":699,"Paid Social":549,"Organic Social":269,"Referral":158,"Unassigned":115,"Cross-network":12,"Paid Other":8,"Email":6},
 "Nueva":{"Organic Search":1837,"Direct":807,"Paid Search":449,"Organic Social":365,"Referral":223,"Cross-network":210,"Unassigned":68,"Paid Social":60,"Email":1},
 "Azzurra":{"Email":624,"Organic Search":572,"Direct":517,"Cross-network":364,"Paid Search":314,"Referral":167,"Paid Social":88,"Unassigned":30,"Organic Social":23,"Paid Other":8},
 "Shiro Sushi":{"Paid Social":949,"Organic Search":843,"Direct":454,"Paid Search":174,"Cross-network":110,"Referral":109,"Unassigned":43,"Organic Social":28,"Paid Other":26,"Email":1},
 "DSL":{"Organic Search":1373,"Direct":1072,"Paid Search":953,"Paid Social":895,"Referral":200,"Cross-network":191,"Unassigned":54,"Organic Social":49,"Paid Other":21,"Email":4}}
CHB_Y={
 "Aqua Shard":{"Paid Search":564,"Direct":513,"Organic Search":341,"Referral":282,"Cross-network":120,"Paid Social":92,"Unassigned":14,"Organic Social":6,"Paid Other":1},
 "Hutong":{"Direct":338,"Organic Search":208,"Cross-network":130,"Referral":129,"Paid Search":102,"Paid Social":52,"Unassigned":14,"Email":9,"Organic Social":2,"Paid Other":1},
 "Kyoto":{"Organic Search":85,"Direct":51,"Paid Search":22,"Unassigned":9,"Referral":2,"Organic Social":1,"Paid Social":1},
 "Nueva":{"Organic Search":56,"Direct":46,"Paid Search":10,"Cross-network":8,"Referral":7,"Organic Social":3,"Unassigned":2},
 "Azzurra":{"Organic Search":30,"Direct":27,"Paid Search":15,"Cross-network":8,"Referral":4,"Email":1,"Paid Social":1,"Unassigned":1},
 "Shiro Sushi":{"Organic Search":44,"Direct":43,"Paid Search":10,"Unassigned":6,"Cross-network":4,"Paid Social":2},
 "DSL":{"Organic Search":76,"Direct":65,"Paid Search":41,"Paid Social":11,"Referral":7,"Unassigned":7,"Cross-network":4,"Paid Other":1}}

# ---------------- META ----------------
# cur/yoy per meta-account: [spend,impr,clicks,sched]
METAC={
 "Aqua Shard":[3023.61,463133,14921,168],"Hutong":[2141.39,331207,11909,211],
 "Kyoto":[450.30,64622,2256,31],"Nueva":[571.37,93336,3664,36],
 "Azzurra":[566.98,115749,1953,40],"Shiro Sushi":[314.04,70421,1397,40],"DSL":[1814.18,251708,8155,139]}
METAY={
 "Aqua Shard":[1090.06,175481,9874,130],"Hutong":[632.13,115868,7373,68],
 "Kyoto":[272.16,40676,1482,12],"Nueva":[381.64,40081,1238,9],
 "Azzurra":[280.42,39966,723,13],"Shiro Sushi":[354.71,69982,3186,23],"DSL":[574.97,71018,3150,38]}
# meta cur campaigns [name,spend,sched] (Regent gets Kyoto/Nueva suffixes)
METACAMP={
 "Aqua Shard":[["CRKLR | Prospecting Campaign",2578.1,166],["CRKLR | Traffic",445.51,2]],
 "Hutong":[["CRKLR - Prospecting Campaign – Tactical",1546.28,124],["CRKLR - Prospecting Campaign",483.69,76],["CRKLR - Remarketing Campaign",111.42,11]],
 "Kyoto":[["CRKLR - Prospecting Campaign V2 (Kyoto)",346.54,16],["CRKLR - Weekend Brunch Focus (Kyoto)",103.76,15]],
 "Nueva":[["CRKLR - Prospecting Campaign (Nueva)",275.31,31],["CRKLR - Prospecting Campaign – Tactical (Nueva)",224.69,4],["CRKLR - Playa Rooftop Terrace (Nueva)",71.37,1]],
 "Azzurra":[["CRKLR - Prospecting Campaign",528.91,37],["CRKLR - Jazz Night Campaign",38.07,3]],
 "Shiro Sushi":[["CRKLR - Leads Campaign – Consolidated",314.04,40]],
 "DSL":[["CRKLR - DSL Prospecting Campaign",1814.18,139]]}
# meta prior campaign spend map (last week cur)
METAPRIOR={
 "Aqua Shard":{"CRKLR | Prospecting Campaign":2440.48,"CRKLR | Traffic":401.09},
 "Hutong":{"CRKLR - Prospecting Campaign – Tactical":1559.67,"CRKLR - Prospecting Campaign":508.27,"CRKLR - Remarketing Campaign":113.78},
 "Regent St":{"CRKLR - Prospecting Campaign V2 (Kyoto)":357.8,"CRKLR - Weekend Brunch Focus (Kyoto)":107.74,"CRKLR - Prospecting Campaign (Nueva)":282.48,"CRKLR - Prospecting Campaign – Tactical (Nueva)":227.3,"CRKLR - Playa Rooftop Terrace (Nueva)":68.45},
 "Azzurra":{"CRKLR - Prospecting Campaign":864.93,"CRKLR - Jazz Night Campaign":285.96},
 "Shiro Sushi":{"CRKLR - Leads Campaign – Consolidated":310.17},
 "DSL":{"CRKLR - DSL Prospecting Campaign":1847.62}}

# ---------------- GOOGLE ----------------
# cur per venue: totals [spend,impr,clicks,book]  + campaigns [name,spend,allconv]
GOOGC={
 "Aqua Shard":{"tot":[5569.52,219565,9986,413],"camp":[["Search > Shard",1341.35,723],["P. Max > Generic",1132.61,1329],["Search > Competitor",15.79,3],["Search > Restaurant",686.97,388],["Search > Brand",58.01,69],["Search > Generic-Occasion",1220.82,174],["Search > Location-Landmark",292.11,59],["Search > View-Experience",439.41,130],["Search > Maps & Local Action",22.94,43],["Demand Gen > Generic",359.51,153]]},
 "Hutong":{"tot":[1380.29,57408,3875,214],"camp":[["Search > Shard",279.00,57],["P. Max > Hutong",277.66,451],["Search > Restaurant",196.01,34],["Search > Brand",197.89,189],["Search > Golden Sky",132.12,409],["Search > Lunch",297.61,318]]},
 "Regent St":{"tot":[701.95,31746,1399,55],"camp":[["Search > Kyoto > Restaurant Type",186.14,84],["Search > Kyoto > Location",185.62,34],["Search > Kyoto > Brunch and Sushi Extravaganza",202.44,82],["PMax > Aqua Nueva",127.75,319]]},
 "Azzurra":{"tot":[640.64,14400,797,15],"camp":[["Search > Brand",243.94,12],["P. Max > Generic",205.91,393],["Search > Private Events",91.47,1],["Search > Restaurant",18.85,1],["Search > Local Discovery",80.47,0]]},
 "Shiro Sushi":{"tot":[726.70,106916,1175,93],"camp":[["Pmax > Generic",325.85,573],["Search > Brand",196.30,147],["Search > Restaurant",204.55,331]]},
 "DSL":{"tot":[269.99,3734,390,26],"camp":[["PMax > Generic",132.72,24],["Search > Brand",38.18,22],["Search > Restaurant",38.08,5],["Search > Afternoon Tea",61.01,15]]}}
# google yoy totals [spend,impr,clicks,book]
GOOGY={
 "Aqua Shard":[2163.87,94008,12394,1096],"Hutong":[1327.45,78722,4793,391],
 "Regent St":[1086.85,71122,2002,77],"Azzurra":[583.29,23249,1124,23],
 "Shiro Sushi":[628.26,420517,1427,57],"DSL":[0,0,0,0]}
# google prior campaign spend (last week cur)
GOOGPRIOR={
 "Aqua Shard":{"Search > Shard":431.08,"P. Max > Generic":294.26,"Search > Generic-Occasion":288.11,"Search > Location-Landmark":237.84,"Search > Afternoon Tea":211.02,"Search > Brand":61.76},
 "Hutong":{"Search > Lunch":373.64,"P. Max > Hutong":318.16,"Search > Shard":278.07,"Search > Golden Sky":176.21,"Search > Brand":165.79},
 "Regent St":{"Search > Kyoto > Location":217.26,"Search > Kyoto > Restaurant Type":210.66,"Search > Kyoto > Brunch and Sushi Extravaganza":206.88,"PMax > Aqua Nueva":147.74},
 "Azzurra":{"Search > Brand":298.29,"P. Max > Generic":215.52,"Search > Local Discovery":79.45,"Search > Restaurant":38.91},
 "Shiro Sushi":{"Pmax > Generic":370.18,"Search > Brand":231.07,"Search > Restaurant":150.14},
 "DSL":{"PMax > Generic":136.72,"Search > Afternoon Tea":73.68,"Search > Restaurant":32.56,"Search > Brand":31.50}}

# 8wk trend spend base (last week W18..W25)
TREND_SPEND_LW={
 "Aqua Shard":[2976,3245,3572,3797,3532,4831,3889,4809],
 "Hutong":[3049,2604,2536,3847,4266,2901,3467,3663],
 "Regent St":[3089,2165,1962,2710,1721,2553,2027,1826],
 "Azzurra":[3185,1416,1132,1257,1545,1488,1700,1814],
 "Shiro Sushi":[894,967,1183,715,514,990,896,1078],
 "DSL":[3684,2176,1763,2715,2838,2226,2066,2122]}
# last week ty_book_weeks (W18..W25)
TYB_LW={"Aqua Shard":[1299,1159,1070,1114,1180,1175,1201,1328],"Hutong":[807,623,626,666,699,676,669,871],
 "Regent St":[263,320,344,409,428,341,266,321],"Azzurra":[124,100,83,100,99,98,83,90],
 "Shiro Sushi":[118,118,118,139,114,124,111,117],"DSL":[450,525,443,460,577,578,546,571]}

# ---- helpers to build per-venue GA4 web/channels ----
def web_metrics(key):
    u,s,spv,dur,eng,nu=WEBC[key]
    return {"avgsec":round(dur,1),"engrate":round(eng*100,1),"pps":round(spv/s,2),"newpct":round(nu/u*100,1)}
def regent_eng():
    k=WEBC["Kyoto"]; n=WEBC["Nueva"]; ks=k[1]; ns=n[1]
    avgsec=(k[3]*ks+n[3]*ns)/(ks+ns)
    eng=(k[4]*ks+n[4]*ns)/(ks+ns)*100
    pps=(k[2]+n[2])/(ks+ns)
    newpct=(k[5]+n[5])/(k[0]+n[0])*100
    return {"avgsec":round(avgsec,1),"engrate":round(eng,1),"pps":round(pps,2),"newpct":round(newpct,1)}

# per-venue cur users/sessions/bookings, yoy users/sessions/bookings, engagement
def ga_web(v):
    if v=="Regent St":
        cu=WEBC["Kyoto"][0]+WEBC["Nueva"][0]; cs=WEBC["Kyoto"][1]+WEBC["Nueva"][1]
        cb=sum(CHB_C["Kyoto"].values())+sum(CHB_C["Nueva"].values())
        yu=WEBY["Kyoto"][0]+WEBY["Nueva"][0]; ys=WEBY["Kyoto"][1]+WEBY["Nueva"][1]
        yb=sum(CHB_Y["Kyoto"].values())+sum(CHB_Y["Nueva"].values())
        eng=regent_eng()
    else:
        cu=WEBC[v][0]; cs=WEBC[v][1]; cb=sum(CHB_C[v].values())
        yu=WEBY[v][0]; ys=WEBY[v][1]; yb=sum(CHB_Y[v].values())
        eng=web_metrics(v)
    pr=LP[v]["web"]["cur"]  # last week cur = this week prior
    def mk(b,u,s): return {"bookings":b,"users":u,"sessions":s,**eng}
    return {"cur":mk(cb,cu,cs),"prior":mk(pr["bookings"],pr["users"],pr["sessions"]),"yoy":mk(yb,yu,ys)}

def merge(d1,d2):
    r=dict(d1)
    for k,val in d2.items(): r[k]=r.get(k,0)+val
    return r

def ga_channels(v):
    if v=="Regent St":
        cs=merge(CHS_C["Kyoto"],CHS_C["Nueva"]); cb=merge(CHB_C["Kyoto"],CHB_C["Nueva"])
        ys=merge(CHS_Y["Kyoto"],CHS_Y["Nueva"]); yb=merge(CHB_Y["Kyoto"],CHB_Y["Nueva"])
    else:
        cs=CHS_C[v]; cb=CHB_C[v]; ys=CHS_Y[v]; yb=CHB_Y[v]
    priorS={c["name"]:c["s"][0] for c in LP[v]["channels"]}
    priorB={c["name"]:c["b"][0] for c in LP[v]["channels"]}
    names=list(cs.keys())
    rows=[]
    for n in names:
        rows.append({"name":n,
            "s":[cs.get(n,0),priorS.get(n,0),ys.get(n,0)],
            "b":[cb.get(n,0),priorB.get(n,0),yb.get(n,0)]})
    rows.sort(key=lambda r:-r["s"][0])
    return rows[:7]

def ga_devices(v):
    if v=="Regent St":
        m=DEVC["Kyoto"][0]+DEVC["Nueva"][0]; d=DEVC["Kyoto"][1]+DEVC["Nueva"][1]; t=DEVC["Kyoto"][2]+DEVC["Nueva"][2]
    else:
        m,d,t=DEVC[v]
    tot=m+d+t
    return {"Mobile":round(m/tot*100),"Desktop":round(d/tot*100),"Tablet":round(t/tot*100)}, (m,d,t)

# ---- meta block ----
def meta_block(v):
    if v=="Regent St":
        cur=[METAC["Kyoto"][i]+METAC["Nueva"][i] for i in range(4)]
        yo=[METAY["Kyoto"][i]+METAY["Nueva"][i] for i in range(4)]
    else:
        cur=METAC[v]; yo=METAY[v]
    pr=LP[v]["ads"]["meta"]["cur"]
    def mk(a): return {"spend":round(a[0],2),"bookings":a[3],"impr":a[1],"clicks":a[2]}
    return {"cur":mk(cur),"prior":{"spend":pr["spend"],"bookings":pr["bookings"],"impr":pr["impr"],"clicks":pr["clicks"]},"yoy":mk(yo)}

def google_block(v):
    c=GOOGC[v]["tot"]; y=GOOGY[v]; pr=LP[v]["ads"]["google"]["cur"]
    return {"cur":{"spend":round(c[0],2),"bookings":c[3],"impr":c[1],"clicks":c[2]},
            "prior":{"spend":pr["spend"],"bookings":pr["bookings"],"impr":pr["impr"],"clicks":pr["clicks"]},
            "yoy":{"spend":round(y[0],2),"bookings":y[3],"impr":y[1],"clicks":y[2]}}

def wow(cur,prior):
    if prior is None or prior==0: return "up"
    if cur>prior*1.02: return "up"
    if cur<prior*0.98: return "down"
    return "flat"

def campaigns_block(v):
    out=[]
    mp=METAPRIOR.get(v,{})
    if v=="Regent St":
        mc=METACAMP["Kyoto"]+METACAMP["Nueva"]
    else:
        mc=METACAMP[v]
    for name,spend,bk in mc:
        out.append({"name":norm(name),"platform":"Meta","spend":round(spend),"bookings":bk,"wow":wow(spend,mp.get(name))})
    gp=GOOGPRIOR.get(v,{})
    for name,spend,bk in GOOGC[v]["camp"]:
        nm=norm(name)
        out.append({"name":nm,"platform":"Google","spend":round(spend),"bookings":bk,"wow":wow(spend,gp.get(nm))})
    out.sort(key=lambda c:-c["bookings"])
    return out[:5]

def funnel_block(m,g,ch):
    impr=m["cur"]["impr"]+g["cur"]["impr"]
    clicks=m["cur"]["clicks"]+g["cur"]["clicks"]
    ps=next((c["s"][0] for c in ch if c["name"]=="Paid Search"),0)
    pso=next((c["s"][0] for c in ch if c["name"]=="Paid Social"),0)
    bk=m["cur"]["bookings"]+g["cur"]["bookings"]
    return {"impr":impr,"clicks":clicks,"landing":ps+pso,"bookings":bk}

def trend_block(v,web_cur_book):
    sp=TREND_SPEND_LW[v][1:]+[round(METAC.get(v,[0])[0] if False else 0)]  # placeholder
    # W26 spend = meta cur + google cur (rounded)
    if v=="Regent St":
        meta_sp=METAC["Kyoto"][0]+METAC["Nueva"][0]
    else:
        meta_sp=METAC[v][0]
    w26=round(meta_sp+GOOGC[v]["tot"][0])
    spend=TREND_SPEND_LW[v][1:]+[w26]
    bookings=TYB_LW[v][1:]+[web_cur_book]
    return {"spend":spend,"bookings":bookings}

DEV_RAW={}
data={}
for v in VEN:
    web=ga_web(v); ch=ga_channels(v); dev,devraw=ga_devices(v); DEV_RAW[v]=devraw
    m=meta_block(v); g=google_block(v)
    data[v]={"web":web,"ads":{"meta":m,"google":g},"channels":ch,"devices":dev,
             "landing":[{"path":p,"s":s,"b":b} for p,s,b in LANDC[v]],
             "trend":trend_block(v,web["cur"]["bookings"]),
             "funnel":funnel_block(m,g,ch),"campaigns":campaigns_block(v)}

# ---------------- ALL ----------------
def all_block():
    W={}
    for pk in ["cur","prior","yoy"]:
        u=sum(data[v]["web"][pk]["users"] for v in VEN)
        s=sum(data[v]["web"][pk]["sessions"] for v in VEN)
        b=sum(data[v]["web"][pk]["bookings"] for v in VEN)
        W[pk]={"bookings":b,"users":u,"sessions":s}
    scur=sum(data[v]["web"]["cur"]["sessions"] for v in VEN)
    ucur=sum(data[v]["web"]["cur"]["users"] for v in VEN)
    avgsec=round(sum(data[v]["web"]["cur"]["avgsec"]*data[v]["web"]["cur"]["sessions"] for v in VEN)/scur,1)
    eng=round(sum(data[v]["web"]["cur"]["engrate"]*data[v]["web"]["cur"]["sessions"] for v in VEN)/scur,1)
    pps=round(sum(data[v]["web"]["cur"]["pps"]*data[v]["web"]["cur"]["sessions"] for v in VEN)/scur,2)
    newpct=round(sum(data[v]["web"]["cur"]["newpct"]*data[v]["web"]["cur"]["users"] for v in VEN)/ucur,1)
    web={}
    for pk in ["cur","prior","yoy"]:
        web[pk]={"bookings":W[pk]["bookings"],"users":W[pk]["users"],"sessions":W[pk]["sessions"],
                 "avgsec":avgsec,"engrate":eng,"pps":pps,"newpct":newpct}
    def sads(plat):
        r={}
        for pk in ["cur","prior","yoy"]:
            r[pk]={k:(round(sum(data[v]["ads"][plat][pk][k] for v in VEN),2) if k=="spend" else sum(data[v]["ads"][plat][pk][k] for v in VEN)) for k in ("spend","bookings","impr","clicks")}
        return r
    meta=sads("meta"); google=sads("google")
    chm={}
    for v in VEN:
        for c in data[v]["channels"]:
            if c["name"] not in chm: chm[c["name"]]={"s":[0,0,0],"b":[0,0,0]}
            for i in range(3): chm[c["name"]]["s"][i]+=c["s"][i]; chm[c["name"]]["b"][i]+=c["b"][i]
    chan=[{"name":n,"s":d["s"],"b":d["b"]} for n,d in sorted(chm.items(),key=lambda kv:-kv[1]["s"][0])[:7]]
    dm=sum(DEV_RAW[v][0] for v in VEN); dd=sum(DEV_RAW[v][1] for v in VEN); dt=sum(DEV_RAW[v][2] for v in VEN)
    tot=dm+dd+dt; dev={"Mobile":round(dm/tot*100),"Desktop":round(dd/tot*100),"Tablet":round(dt/tot*100)}
    hs=hb=ss=sb=ms=mb=0
    for v in VEN:
        for L in LANDC[v]:
            p,s,b=L
            if p=="/" or p.startswith("/ ("): hs+=s; hb+=b
            elif "reservations/create/search" in p: ss+=s; sb+=b
            elif p=="/menus" or p.startswith("/menus ("): ms+=s; mb+=b
    pp=next((L for L in LANDC["Aqua Shard"] if L[0]=="/peter-pan-afternoon-tea"),["",0,0])
    lp=next((L for L in LANDC["Hutong"] if L[0]=="/menus/lunch-ppc"),["",0,0])
    land=[{"path":"/ (all venues)","s":hs,"b":hb},
          {"path":"reservations/create/search (all venues)","s":ss,"b":sb},
          {"path":"/menus (all venues)","s":ms,"b":mb},
          {"path":"/peter-pan-afternoon-tea (Shard)","s":pp[1],"b":pp[2]},
          {"path":"/menus/lunch-ppc (Hutong)","s":lp[1],"b":lp[2]}]
    tr={"spend":[sum(data[v]["trend"]["spend"][i] for v in VEN) for i in range(8)],
        "bookings":[sum(data[v]["trend"]["bookings"][i] for v in VEN) for i in range(8)]}
    fn={"impr":sum(data[v]["funnel"]["impr"] for v in VEN),"clicks":sum(data[v]["funnel"]["clicks"] for v in VEN),
        "landing":sum(data[v]["funnel"]["landing"] for v in VEN),"bookings":sum(data[v]["funnel"]["bookings"] for v in VEN)}
    allc=[]
    for v in VEN:
        vs={"Aqua Shard":"Shard","Regent St":"Kyoto/Nueva"}.get(v,v)
        for c in data[v]["campaigns"]:
            cc=dict(c); cc["name"]=c["name"]+f" ({vs})"; allc.append(cc)
    allc.sort(key=lambda c:-c["bookings"])
    return {"web":web,"ads":{"meta":meta,"google":google},"channels":chan,"devices":dev,
            "landing":land,"trend":tr,"funnel":fn,"campaigns":allc[:5]}

data["All"]=all_block()
payload={"market":"London","sym":"£","week":"W26 · 27 Jul–2 Aug 2026","fy":"FY26",
         "venues":["All"]+VEN,"data":data}
json.dump(payload,open(OUT,"w"),indent=1,ensure_ascii=False)
A=data["All"]
print("ALL web: bk",A["web"]["cur"]["bookings"],"/ prior",A["web"]["prior"]["bookings"],"/ yoy",A["web"]["yoy"]["bookings"])
print("ALL users: cur",A["web"]["cur"]["users"],"prior",A["web"]["prior"]["users"],"yoy",A["web"]["yoy"]["users"])
print("ALL meta spend cur",A["ads"]["meta"]["cur"]["spend"],"prior",A["ads"]["meta"]["prior"]["spend"],"yoy",A["ads"]["meta"]["yoy"]["spend"])
print("ALL google spend cur",A["ads"]["google"]["cur"]["spend"],"prior",A["ads"]["google"]["prior"]["spend"],"yoy",A["ads"]["google"]["yoy"]["spend"])
tot_cur=round(A["ads"]["meta"]["cur"]["spend"]+A["ads"]["google"]["cur"]["spend"],2)
tot_pr=round(A["ads"]["meta"]["prior"]["spend"]+A["ads"]["google"]["prior"]["spend"],2)
tot_yo=round(A["ads"]["meta"]["yoy"]["spend"]+A["ads"]["google"]["yoy"]["spend"],2)
print("ALL total ad spend cur",tot_cur,"prior",tot_pr,"yoy",tot_yo)
print("ALL ad-driven bookings: cur",A["ads"]["meta"]["cur"]["bookings"]+A["ads"]["google"]["cur"]["bookings"],
      "prior",A["ads"]["meta"]["prior"]["bookings"]+A["ads"]["google"]["prior"]["bookings"],
      "yoy",A["ads"]["meta"]["yoy"]["bookings"]+A["ads"]["google"]["yoy"]["bookings"])
print("trend spend last",A["trend"]["spend"][-1],"trend bk last",A["trend"]["bookings"][-1])
for v in VEN:
    d=data[v]; print(v,"bk",d["web"]["cur"]["bookings"],"meta",d["ads"]["meta"]["cur"]["spend"],"goog",d["ads"]["google"]["cur"]["spend"])
