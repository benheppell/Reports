import json
R="/sessions/vibrant-nice-lamport/mnt/Hong Kong/site/london/w2026-07-20/_adsraw/"
RAW="/sessions/vibrant-nice-lamport/mnt/Hong Kong/site/london/w2026-07-20/_raw/"
OUT="/sessions/vibrant-nice-lamport/mnt/Hong Kong/site/london/w2026-07-20/"
L=lambda f: json.load(open(f))
shard=L(R+"shard.json"); hutong=L(R+"hutong.json"); kyoto=L(R+"kyoto.json"); nueva=L(R+"nueva.json")
azzurra=L(R+"azzurra.json"); shiro=L(R+"shiro.json"); dsl=L(R+"dsl.json")
meta_cur=L(R+"meta_cur.json"); meta_pa=L(R+"meta_pa.json")
google_cur=L(R+"google_cur.json"); google_pa=L(R+"google_pa.json")
gty=L(RAW+"google_ty.json"); gly=L(RAW+"google_ly.json")
tyb=L(RAW+"ty_book_weeks.json"); lyb=L(RAW+"ly_book.json")
wowp=L(R+"wow_prior.json")

VEN=["Aqua Shard","Hutong","Regent St","Azzurra","Shiro Sushi","DSL"]

# ---- Regent combined GA4 ----
def comb_regent():
    k,n=kyoto,nueva
    w={}
    users=[k["web"]["users"][i]+n["web"]["users"][i] for i in range(3)]
    sess=[k["web"]["sessions"][i]+n["web"]["sessions"][i] for i in range(3)]
    ks,ns=k["web"]["sessions"][0],n["web"]["sessions"][0]
    avgsec=(k["web"]["avgsec"]*ks+n["web"]["avgsec"]*ns)/(ks+ns)
    engrate=(k["web"]["engrate"]*ks+n["web"]["engrate"]*ns)/(ks+ns)
    pps=(k["web"]["spv_cur"]+n["web"]["spv_cur"])/(ks+ns)
    newpct=(k["web"]["newusers_cur"]+n["web"]["newusers_cur"])/(k["web"]["users"][0]+n["web"]["users"][0])*100
    # bookings from tyb/lyb
    bk=[tyb["Regent St"][-1],tyb["Regent St"][-2],lyb["yoy"]["Regent St"]]
    web={"users":users,"sessions":sess,"avgsec":round(avgsec,1),"engrate":round(engrate,1),
         "spv_cur":k["web"]["spv_cur"]+n["web"]["spv_cur"],"newusers_cur":k["web"]["newusers_cur"]+n["web"]["newusers_cur"],
         "bookings":bk,"pps_pre":pps,"newpct_pre":newpct}
    # channels merge
    ch={}
    for src in (k["channels"],n["channels"]):
        for name,d in src.items():
            if name not in ch: ch[name]={"s":[0,0,0],"b":[0,0,0]}
            for i in range(3):
                ch[name]["s"][i]+=d["s"][i]; ch[name]["b"][i]+=d["b"][i]
    dev={x:k["devices"][x]+n["devices"][x] for x in k["devices"]}
    land=sorted(k["landing"]+n["landing"],key=lambda r:-r[1])[:5]
    return {"web":web,"channels":ch,"devices":dev,"landing":land}

regent=comb_regent()
GA={"Aqua Shard":shard,"Hutong":hutong,"Regent St":regent,"Azzurra":azzurra,"Shiro Sushi":shiro,"DSL":dsl}

def webblock(g):
    w=g["web"]
    if "pps_pre" in w:
        pps=round(w["pps_pre"],2); newpct=round(w["newpct_pre"],1)
    else:
        pps=round(w["spv_cur"]/w["sessions"][0],2); newpct=round(w["newusers_cur"]/w["users"][0]*100,1)
    avgsec=w["avgsec"]; eng=w["engrate"]
    def mk(i): return {"bookings":w["bookings"][i],"users":w["users"][i],"sessions":w["sessions"][i],
                       "avgsec":avgsec,"engrate":eng,"pps":pps,"newpct":newpct}
    return {"cur":mk(0),"prior":mk(1),"yoy":mk(2)}

# ---- meta per venue ----
def meta_block(v):
    if v=="Regent St":
        cur={x:meta_cur["Kyoto"][x]+meta_cur["Nueva"][x] for x in ("spend","impr","clicks","sched")}
        pr={x:meta_pa["prior"]["Kyoto"][x]+meta_pa["prior"]["Nueva"][x] for x in ("spend","impr","clicks","sched")}
        yo={x:meta_pa["yoy"]["Kyoto"][x]+meta_pa["yoy"]["Nueva"][x] for x in ("spend","impr","clicks","sched")}
    else:
        c=meta_cur[v]; cur={"spend":c["spend"],"impr":c["impr"],"clicks":c["clicks"],"sched":c["sched"]}
        pr=meta_pa["prior"][v]; yo=meta_pa["yoy"][v]
    def mk(d): return {"spend":round(d["spend"],2),"bookings":d["sched"],"impr":d["impr"],"clicks":d["clicks"]}
    return {"cur":mk(cur),"prior":mk(pr),"yoy":mk(yo)}

def google_block(v):
    gc=google_cur[v]; gp=google_pa
    bk_cur=round(gty[v]["book"][-1]); bk_pr=round(gty[v]["book"][-2]); bk_yo=round(gly[v]["book"][-1])
    cur={"spend":round(gc["cost"],2),"bookings":bk_cur,"impr":gc["impr"],"clicks":gc["clicks"]}
    pr={"spend":round(gp["prior"][v]["cost"],2),"bookings":bk_pr,"impr":gp["prior"][v]["impr"],"clicks":gp["prior"][v]["clicks"]}
    yo={"spend":round(gp["yoy"][v]["cost"],2),"bookings":bk_yo,"impr":gp["yoy"][v]["impr"],"clicks":gp["yoy"][v]["clicks"]}
    return {"cur":cur,"prior":pr,"yoy":yo}

def channels_block(g):
    ch=g["channels"]
    items=sorted(ch.items(),key=lambda kv:-kv[1]["s"][0])[:7]
    return [{"name":n,"s":d["s"],"b":d["b"]} for n,d in items]

def devices_block(g):
    d=g["devices"]; tot=d["mobile"]+d["desktop"]+d["tablet"]
    m=round(d["mobile"]/tot*100); de=round(d["desktop"]/tot*100); t=round(d["tablet"]/tot*100)
    return {"Mobile":m,"Desktop":de,"Tablet":t}

def landing_block(g):
    return [{"path":p,"s":s,"b":b} for p,s,b in g["landing"][:5]]

# ---- trend (embedded spend W18..W25, bookings from tyb) ----
TREND_SPEND={
 "Aqua Shard":[2976,3245,3572,3797,3532,4831,3889,4809],
 "Hutong":[3049,2604,2536,3847,4266,2901,3467,3663],
 "Regent St":[3089,2165,1962,2710,1721,2553,2027,1826],
 "Azzurra":[3185,1416,1132,1257,1545,1488,1700,1814],
 "Shiro Sushi":[894,967,1183,715,514,990,896,1078],
 "DSL":[3684,2176,1763,2715,2838,2226,2066,2122]}
def trend_block(v):
    return {"spend":TREND_SPEND[v],"bookings":tyb[v]}

# ---- campaigns ----
META_PRIOR={
 "Aqua Shard":{"CRKLR | Prospecting Campaign":2188.93,"CRKLR | Traffic":349.95},
 "Hutong":{"CRKLR - Prospecting Campaign – Tactical":1490.37,"CRKLR - Prospecting Campaign":474.6,"CRKLR - Remarketing Campaign":109.71},
 "Regent St":{"CRKLR - Prospecting Campaign V2 (Kyoto)":341.53,"CRKLR - Weekend Brunch Focus (Kyoto)":101.06,"CRKLR - Prospecting Campaign (Nueva)":278.28,"CRKLR - Prospecting Campaign – Tactical (Nueva)":221.09,"CRKLR - Playa Rooftop Terrace (Nueva)":70.43},
 "Azzurra":{"CRKLR - Prospecting Campaign":804.65,"CRKLR - Jazz Night Campaign":270.3},
 "Shiro Sushi":{"CRKLR - Leads Campaign – Consolidated":310.17},
 "DSL":{"CRKLR - DSL Prospecting Campaign":1791.07}}
def wow(cur,prior):
    if prior is None or prior==0: return "up"
    if cur>prior*1.02: return "up"
    if cur<prior*0.98: return "down"
    return "flat"
def campaigns_block(v):
    out=[]
    # meta
    mc = (meta_cur["Kyoto"]["campaigns"]+meta_cur["Nueva"]["campaigns"]) if v=="Regent St" else meta_cur[v]["campaigns"]
    for name,spend,bk in mc:
        pr=META_PRIOR[v].get(name)
        out.append({"name":name,"platform":"Meta","spend":round(spend),"bookings":bk,"wow":wow(spend,pr)})
    # google
    for name,spend,bk in google_cur[v]["campaigns"]:
        pr=wowp["google"][v].get(name)
        out.append({"name":name,"platform":"Google","spend":round(spend),"bookings":bk,"wow":wow(spend,pr)})
    out.sort(key=lambda c:-c["bookings"])
    return out[:5]

def funnel_block(m,g,ch):
    impr=m["cur"]["impr"]+g["cur"]["impr"]
    clicks=m["cur"]["clicks"]+g["cur"]["clicks"]
    ps=next((c["s"][0] for c in ch if c["name"]=="Paid Search"),0)
    pso=next((c["s"][0] for c in ch if c["name"]=="Paid Social"),0)
    bk=m["cur"]["bookings"]+g["cur"]["bookings"]
    return {"impr":impr,"clicks":clicks,"landing":ps+pso,"bookings":bk}

data={}
for v in VEN:
    g=GA[v]; web=webblock(g); m=meta_block(v); go=google_block(v)
    ch=channels_block(g)
    data[v]={"web":web,"ads":{"meta":m,"google":go},"channels":ch,
             "devices":devices_block(g),"landing":landing_block(g),
             "trend":trend_block(v),"funnel":funnel_block(m,go,ch),
             "campaigns":campaigns_block(v)}

# ---- ALL aggregate ----
def all_block():
    # web
    def sweb(i,key): return sum(data[v]["web"][["cur","prior","yoy"][i]][key] for v in VEN)
    web={}
    for pi,pk in enumerate(["cur","prior","yoy"]):
        users=sum(data[v]["web"][pk]["users"] for v in VEN)
        sess=sum(data[v]["web"][pk]["sessions"] for v in VEN)
        book=sum(data[v]["web"][pk]["bookings"] for v in VEN)
        web[pk]={"users":users,"sessions":sess,"bookings":book}
    # weighted rates (cur)
    scur=sum(data[v]["web"]["cur"]["sessions"] for v in VEN)
    ucur=sum(data[v]["web"]["cur"]["users"] for v in VEN)
    avgsec=round(sum(data[v]["web"]["cur"]["avgsec"]*data[v]["web"]["cur"]["sessions"] for v in VEN)/scur,1)
    eng=round(sum(data[v]["web"]["cur"]["engrate"]*data[v]["web"]["cur"]["sessions"] for v in VEN)/scur,1)
    pps=round(sum(data[v]["web"]["cur"]["pps"]*data[v]["web"]["cur"]["sessions"] for v in VEN)/scur,2)
    newpct=round(sum(data[v]["web"]["cur"]["newpct"]*data[v]["web"]["cur"]["users"] for v in VEN)/ucur,1)
    W={}
    for pk in ["cur","prior","yoy"]:
        W[pk]={"bookings":web[pk]["bookings"],"users":web[pk]["users"],"sessions":web[pk]["sessions"],
               "avgsec":avgsec,"engrate":eng,"pps":pps,"newpct":newpct}
    # ads
    def sads(plat):
        r={}
        for pk in ["cur","prior","yoy"]:
            r[pk]={k:round(sum(data[v]["ads"][plat][pk][k] for v in VEN),2) if k=="spend" else sum(data[v]["ads"][plat][pk][k] for v in VEN) for k in ("spend","bookings","impr","clicks")}
        return r
    meta=sads("meta"); google=sads("google")
    # channels
    ch={}
    for v in VEN:
        for c in data[v]["channels"]:
            if c["name"] not in ch: ch[c["name"]]={"s":[0,0,0],"b":[0,0,0]}
            for i in range(3): ch[c["name"]]["s"][i]+=c["s"][i]; ch[c["name"]]["b"][i]+=c["b"][i]
    chan=[{"name":n,"s":d["s"],"b":d["b"]} for n,d in sorted(ch.items(),key=lambda kv:-kv[1]["s"][0])[:7]]
    # devices weighted
    dm=sum(GA[v]["devices"]["mobile"] for v in VEN); dd=sum(GA[v]["devices"]["desktop"] for v in VEN); dt=sum(GA[v]["devices"]["tablet"] for v in VEN)
    tot=dm+dd+dt; dev={"Mobile":round(dm/tot*100),"Desktop":round(dd/tot*100),"Tablet":round(dt/tot*100)}
    # landing grouped
    home_s=home_b=srch_s=srch_b=men_s=men_b=0
    for v in VEN:
        for p,s,b in GA[v]["landing"]:
            if p=="/" or p.startswith("/ ("): home_s+=s; home_b+=b
            elif "reservations/create/search" in p: srch_s+=s; srch_b+=b
            elif p=="/menus" or p.startswith("/menus ("): men_s+=s; men_b+=b
    land=[{"path":"/ (all venues)","s":home_s,"b":home_b},
          {"path":"reservations/create/search (all venues)","s":srch_s,"b":srch_b},
          {"path":"/menus (all venues)","s":men_s,"b":men_b},
          {"path":"/peter-pan-afternoon-tea (Shard)","s":4118,"b":86},
          {"path":"/menus/lunch-ppc (Hutong)","s":3285,"b":43}]
    # trend
    tr={"spend":[sum(TREND_SPEND[v][i] for v in VEN) for i in range(8)],
        "bookings":[sum(tyb[v][i] for v in VEN) for i in range(8)]}
    # funnel
    fn={"impr":sum(data[v]["funnel"]["impr"] for v in VEN),"clicks":sum(data[v]["funnel"]["clicks"] for v in VEN),
        "landing":sum(data[v]["funnel"]["landing"] for v in VEN),"bookings":sum(data[v]["funnel"]["bookings"] for v in VEN)}
    # campaigns top5 across venues
    allc=[]
    for v in VEN:
        vs={"Aqua Shard":"Shard","Regent St":"Kyoto/Nueva"}.get(v,v)
        for c in data[v]["campaigns"]:
            cc=dict(c); cc["name"]=c["name"]+f" ({vs})" if not c["name"].endswith(")") else c["name"]+f" ({vs})"
            allc.append(cc)
    allc.sort(key=lambda c:-c["bookings"])
    return {"web":W,"ads":{"meta":meta,"google":google},"channels":chan,"devices":dev,
            "landing":land,"trend":tr,"funnel":fn,"campaigns":allc[:5]}

data["All"]=all_block()

payload={"market":"London","sym":"£","week":"W25 · 20–26 Jul 2026","fy":"FY26",
         "venues":["All"]+VEN,"data":data}
json.dump(payload,open(OUT+"_ads_payload.json","w"),indent=1,ensure_ascii=False)
print("All web bookings cur:",data["All"]["web"]["cur"]["bookings"])
print("Portfolio meta cur spend:",data["All"]["ads"]["meta"]["cur"]["spend"],"bookings:",data["All"]["ads"]["meta"]["cur"]["bookings"])
print("Portfolio google cur spend:",data["All"]["ads"]["google"]["cur"]["spend"],"bookings:",data["All"]["ads"]["google"]["cur"]["bookings"])
print("Total ad spend cur:",round(data["All"]["ads"]["meta"]["cur"]["spend"]+data["All"]["ads"]["google"]["cur"]["spend"],2))
for v in VEN: print(v,"web cur bk",data[v]["web"]["cur"]["bookings"],"meta",data[v]["ads"]["meta"]["cur"]["spend"],"goog",data[v]["ads"]["google"]["cur"]["spend"])
