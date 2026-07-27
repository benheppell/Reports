import json
R="/sessions/vibrant-nice-lamport/mnt/Hong Kong/site/london/w2026-07-20/_raw/"
OUT="/sessions/vibrant-nice-lamport/mnt/Hong Kong/site/london/w2026-07-20/"
tyb=json.load(open(R+"ty_book_weeks.json"))        # W18..W25 bookings
lyb=json.load(open(R+"ly_book.json"))              # weeks(LW22-25), yoy(21-27)
tyu=json.load(open(R+"ty_users_weeks.json"))       # W18..W25 daily-sum users
lyu=json.load(open(R+"ly_users.json"))             # weeks LW22-25 daily-sum, yoy
gty=json.load(open(R+"google_ty.json"))
gly=json.load(open(R+"google_ly.json"))
import importlib.util
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
meta=load("meta",R+"meta.py")
VEN=["Aqua Shard","Hutong","Regent St","Azzurra","Shiro Sushi","DSL"]
DEEP=["Aqua Shard","Hutong","Regent St","Azzurra","Shiro Sushi"]

# ---- weekly bookings (W25 current, W24 prior) ----
actW25={v:tyb[v][-1] for v in VEN}
wowW24={v:tyb[v][-2] for v in VEN}
yoy={v:lyb["yoy"][v] for v in VEN}
# targets
tgt={"Aqua Shard":2180,"Hutong":1066,"Regent St":432,"Azzurra":147,"Shiro Sushi":148,"DSL":207}
ytd={"Aqua Shard":33119,"Hutong":18582,"Regent St":7854,"Azzurra":2937,"Shiro Sushi":2649,"DSL":13241}
ytdt={"Aqua Shard":37200,"Hutong":19777,"Regent St":10070,"Azzurra":4133,"Shiro Sushi":3873,"DSL":4488}
# meta/google W25 spend
meta_s={v:meta.ty[v]["spend"][-1] for v in VEN}
meta_sch={v:meta.ty[v]["sch"][-1] for v in VEN}
meta_sch_prior={v:meta.ty[v]["sch"][-2] for v in VEN}
goog_s={v:round(gty[v]["spend"][-1],2) for v in VEN}
goog_c={v:round(gty[v]["book"][-1],6) for v in VEN}
goog_c_prior={v:round(gty[v]["book"][-2],6) for v in VEN}

# ===== DASHBOARD =====
venues=[]
for v in VEN:
    venues.append({"name":v,"act":actW25[v],"tgt":tgt[v],"wow":wowW24[v],"yoy":yoy[v],
                   "ytd":ytd[v],"ytdt":ytdt[v],"meta_s":round(meta_s[v],2),"goog_s":goog_s[v],
                   "nc":(v=="DSL")})
tot_act=sum(actW25[v] for v in VEN); tot_tgt=sum(tgt[v] for v in VEN)
tot_wow=sum(wowW24[v] for v in VEN); tot_yoy=sum(yoy[v] for v in VEN)
tot_ytd=sum(ytd[v] for v in VEN); tot_ytdt=sum(ytdt[v] for v in VEN)
varp=(tot_act-tot_tgt)/tot_tgt*100
wowp=(tot_act-tot_wow)/tot_wow*100
yoyp=(tot_act-tot_yoy)/tot_yoy*100
ytdvarp=(tot_ytd-tot_ytdt)/tot_ytdt*100
below=[(v,(ytd[v]-ytdt[v])/ytdt[v]*100) for v in VEN if ytd[v]<ytdt[v]]
print("PORT act",tot_act,"tgt",tot_tgt,"var%%%.1f"%varp,"wow%%%.1f"%wowp,"yoy%%%.1f"%yoyp,"ytdvar%%%.1f"%ytdvarp)
print("below",[(v,round(p,1)) for v,p in below])
# note
belownames=", ".join("%s (%.0f%%)"%(v,(actW25[v]-tgt[v])/tgt[v]*100) for v in ["Aqua Shard","Hutong","Regent St","Azzurra","Shiro Sushi"] if actW25[v]<tgt[v])
note=(f"<b>Portfolio</b> bookings of {tot_act:,} finished {abs(varp):.0f} percent below the {tot_tgt:,} weekly target, "
      f"though up {wowp:.1f} percent week on week and roughly {'up' if yoyp>=0 else 'down'} {abs(yoyp):.1f} percent versus a year ago. "
      f"Every core venue trades below its weekly goal, led by {belownames}. "
      f"<b>Regent St</b> combines Aqua Kyoto + Aqua Nueva (both GA4 properties and both Meta accounts; Google is a shared account). "
      f"<b>DSL</b> is trading far above a pre-rebrand target, so its variance and YoY are not comparable.")
dash={"market":"London","ccy":"GBP","sym":"£","ytd_label":"FY from Feb","venues":venues,"note":note,
      "week":"20–26 Jul 2026","wow":"13–19 Jul 2026","yoy":"21–27 Jul 2025","generated":"27 July 2026"}
json.dump(dash,open(OUT+"_dashboard_payload.json","w"),indent=1,ensure_ascii=False)

# ===== DEEPDIVE current-week engagement =====
eng={
"Aqua Shard":dict(sessions=33102,users=23473,pv=91508,asd=198.03577538224278,bounce=0.45121140716573016),
"Hutong":dict(sessions=20179,users=14355,pv=57636,asd=197.75852937405222,bounce=0.46538480598642151),
"Kyoto":dict(sessions=5024,users=3822,pv=15232,asd=187.86208559972133,bounce=0.38734076433121017),
"Nueva":dict(sessions=2916,users=2231,pv=8977,asd=161.78882002160498,bounce=0.42078189300411523),
"Azzurra":dict(sessions=2201,users=1807,pv=6169,asd=169.36775333848252,bounce=0.44207178555202181),
"Shiro Sushi":dict(sessions=1777,users=1329,pv=5236,asd=166.85876863308948,bounce=0.34440067529544177),
}
def regent_eng():
    k=eng["Kyoto"];n=eng["Nueva"];s=k["sessions"]+n["sessions"]
    asd=(k["asd"]*k["sessions"]+n["asd"]*n["sessions"])/s
    bo=(k["bounce"]*k["sessions"]+n["bounce"]*n["sessions"])/s
    return dict(sessions=s,users=k["users"]+n["users"],pv=k["pv"]+n["pv"],asd=asd,bounce=bo)
eng["Regent St"]=regent_eng()
dv=[]
for v in DEEP:
    e=eng[v]
    dv.append({"name":v,"act":actW25[v],"tgt":tgt[v],"wow_b":wowW24[v],"yoy_b":yoy[v],
               "users":e["users"],"sessions":e["sessions"],"asd":e["asd"],"bounce":e["bounce"],
               "meta_s":round(meta_s[v],2),"meta_sch":meta_sch[v],"meta_sch_prior":meta_sch_prior[v],
               "goog_s":goog_s[v],"goog_c":goog_c[v],"goog_c_prior":goog_c_prior[v],"shared":(v=="Regent St")})
# series 8-week
labels=["W18","W19","W20","W21","W22","W23","W24","W25"]
series={"labels":labels,"venues":{}}
for v in DEEP:
    series["venues"][v]={"bookings":tyb[v],"users":tyu[v]}
# obs
def cps(v): return meta_s[v]/meta_sch[v] if meta_sch[v] else 0
def gcpa(v): return goog_s[v]/goog_c[v] if goog_c[v] else 0
tot_db=sum(actW25[v] for v in DEEP); tot_dt=sum(tgt[v] for v in DEEP)
meta_obs=[
 f"Shiro Sushi remains the most efficient venue on Meta at £{cps('Shiro Sushi'):.2f} per schedule on the smallest budget of £{meta_s['Shiro Sushi']:,.0f}.",
 f"Hutong scaled hard to {meta_sch['Hutong']} schedules at £{cps('Hutong'):.2f} each, while Aqua Shard sits at £{cps('Aqua Shard'):.2f} on £{meta_s['Aqua Shard']:,.0f} spend.",
 f"Regent St schedules rose WoW to {meta_sch['Regent St']} at £{cps('Regent St'):.2f}; no deep-dive venue breaches the £25 poor mark."]
goog_obs=[
 f"Aqua Shard stays cheapest on Google at £{gcpa('Aqua Shard'):.2f} per booking, though conversions eased WoW from {goog_c_prior['Aqua Shard']:.0f} to {goog_c['Aqua Shard']:.0f}.",
 f"Azzurra is the least efficient at £{gcpa('Azzurra'):.2f} per booking on just {goog_c['Azzurra']:.0f} conversions.",
 f"Shiro Sushi improved to {goog_c['Shiro Sushi']:.0f} bookings at £{gcpa('Shiro Sushi'):.2f}, the only deep-dive venue up week on week."]
ga4_obs=[
 f"Deep-dive bookings of {tot_db:,} sit {abs((tot_db-tot_dt)/tot_dt*100):.0f} percent below the combined {tot_dt:,} target, with every venue behind goal.",
 f"Aqua Shard is {abs((actW25['Aqua Shard']-tgt['Aqua Shard'])/tgt['Aqua Shard']*100):.0f} percent below target and down {abs((actW25['Aqua Shard']-yoy['Aqua Shard'])/yoy['Aqua Shard']*100):.0f} percent YoY, the single largest drag.",
 f"Bookings rose week on week across the set, but Regent St ({actW25['Regent St']}) and Azzurra ({actW25['Azzurra']}) remain the softest against target."]
deepdive={"market":"London","ccy":"GBP","sym":"£","week":"20–26 Jul 2026","wow":"13–19 Jul 2026",
          "yoy":"21–27 Jul 2025","generated":"27 July 2026","badge":"BEHIND TARGET","venues":dv,
          "cpa":{"meta_good":15,"meta_poor":25,"goog_good":18,"goog_poor":30},
          "obs":{"meta":meta_obs,"google":goog_obs,"ga4":ga4_obs},"series":series}
json.dump(deepdive,open(OUT+"_deepdive_payload.json","w"),indent=1,ensure_ascii=False)

# ===== TRENDS =====
# deduped users via ratio
ded_ty={"Aqua Shard":84825,"Hutong":49892,"Regent St":15013+9834,"Azzurra":7359,"Shiro Sushi":4427,"DSL":21811}
ded_ly={"Aqua Shard":118387,"Hutong":52951,"Regent St":18634+12686,"Azzurra":7586,"Shiro Sushi":8785,"DSL":10928}
def ty_users4(v): return tyu[v][4:8]     # W22-25
def ly_users4(v): return lyu["weeks"][v] # LW22-25
def ded_weekly(daily4,ded_total):
    s=sum(daily4); r=ded_total/s if s else 1
    return [int(round(x*r)) for x in daily4]
data={}
for v in VEN:
    tyU=ded_weekly(ty_users4(v),ded_ty[v])
    lyU=ded_weekly(ly_users4(v),ded_ly[v])
    tyB=tyb[v][4:8]; lyB=lyb["weeks"][v]
    tyMs=meta.ty[v]["sch"]; lyMs=meta.ly[v]["sch"]
    tyMsp=meta.ty[v]["spend"]; lyMsp=meta.ly[v]["spend"]
    tyG=gty[v]["book"]; lyG=gly[v]["book"]
    tyGsp=gty[v]["spend"]; lyGsp=gly[v]["spend"]
    tySig=gty[v]["sig"]; lySig=gly[v]["sig"]
    cvr_ty=[round(tyB[i]/tyU[i]*100,2) if tyU[i] else 0 for i in range(4)]
    cvr_ly=[round(lyB[i]/lyU[i]*100,2) if lyU[i] else 0 for i in range(4)]
    gcpa_ty=[round(tyGsp[i]/tyG[i],2) if tyG[i] else 0 for i in range(4)]
    gcpa_ly=[round(lyGsp[i]/lyG[i],2) if lyG[i] else 0 for i in range(4)]
    mcpa_ty=[round(tyMsp[i]/tyMs[i],2) if tyMs[i] else 0 for i in range(4)]
    mcpa_ly=[round(lyMsp[i]/lyMs[i],2) if lyMs[i] else 0 for i in range(4)]
    gbk_ty=[round(x) for x in tyG]; gbk_ly=[round(x) for x in lyG]
    data[v]=[
      ["Website users",tyU,lyU,False,"n"],
      ["Conversion rate",cvr_ty,cvr_ly,False,"%"],
      ["GA4 bookings",tyB,lyB,False,"n"],
      ["Meta bookings",tyMs,lyMs,False,"n"],
      ["Google bookings",gbk_ty,gbk_ly,False,"n"],
      ["Google CPA",gcpa_ty,gcpa_ly,True,"$"],
      ["Meta CPA",mcpa_ty,mcpa_ly,True,"$"],
      ["Google walk-in signals",[round(x) for x in tySig],[round(x) for x in lySig],False,"n"],
    ]
# narratives & alerts
narr={}; alert={}
for v in VEN:
    tyU=data[v][0][1]; lyU=data[v][0][2]
    uyoy=(tyU[-1]-lyU[-1])/lyU[-1]*100 if lyU[-1] else 0
    cvr_t=data[v][1][1][-1]; cvr_l=data[v][1][2][-1]
    gb_t=data[v][2][1][-1]; gb_l=data[v][2][2][-1]
    if v=="DSL":
        narr[v]=(f"DSL (Dim Sum Library) leads the portfolio on conversion at {cvr_t}% on {tyU[-1]:,} users, with GA4 bookings of {gb_t}. "
                 f"NOTE: DSL rebranded, so the 2025 lines are pre-rebrand (Luci) and are NOT a like-for-like comparison — the apparent YoY gains are a rebrand artefact and last year's Google data does not exist on this account.")
        alert[v]=["blue","Not comparable","Pre-rebrand (Luci) baseline last year — YoY lines are not a like-for-like comparison"]
        continue
    trend="up" if uyoy>=0 else "down"
    narr[v]=(f"{v} drew {tyU[-1]:,} users in W25, {abs(uyoy):.0f}% {'above' if uyoy>=0 else 'below'} the same FY week last year, "
             f"with conversion at {cvr_t}% versus {cvr_l}% LY, so GA4 bookings landed at {gb_t} against {gb_l} a year ago. "
             f"Google ran £{gty[v]['spend'][-1]:,.0f} for {gbk_ty if False else round(gty[v]['book'][-1])} bookings; Meta held {meta.ty[v]['sch'][-1]} schedules at £{(meta.ty[v]['spend'][-1]/meta.ty[v]['sch'][-1]) if meta.ty[v]['sch'][-1] else 0:.2f}.")
    if uyoy < -15:
        alert[v]=["red","Traffic drop",f"Latest-week users down {abs(uyoy):.1f}% vs same FY week last year"]
    elif uyoy>=0 and cvr_t<cvr_l:
        alert[v]=["amber","Conversion check",f"Users up {uyoy:.1f}% YoY but conversion rate down to {cvr_t}% from {cvr_l}%"]
    elif cvr_t<cvr_l:
        alert[v]=["amber","Conversion check",f"Users down {abs(uyoy):.1f}% YoY and conversion rate down to {cvr_t}% from {cvr_l}%"]
    else:
        alert[v]=["green","On track",f"Users {('up' if uyoy>=0 else 'down')} {abs(uyoy):.1f}% YoY with conversion holding at {cvr_t}%"]
sharednote={
 "Regent St":"Regent St combines Aqua Kyoto + Aqua Nueva (GA4 users/bookings & Meta spend/schedules summed; Google is a single shared account — Kyoto + Nueva booking actions summed). Walk-in signals are the shared Google account's local actions (Directions + Menu views + Clicks to call; no Store-visit action on this account).",
 "Hutong":"Google bookings sum two booking actions ('Sevenrooms Booking Complete' + 'Hutong UK - GA4 (web) sevenrooms_booking_complete').",
 "Shiro Sushi":"Google bookings sum three booking actions (SST booking_complete + UK sevenrooms_booking_complete + Booking Complete).",
 "Azzurra":"Google account has no Store-visit conversion; walk-in signals cover Directions + Menu views only, and no local actions were recorded last year (LY = 0).",
 "DSL":"DSL Meta account reports as 'Luci' (confirmed mapping). Google account has no 2025 data (post-rebrand build) and no local-action conversions, so LY Google bookings/CPA and all walk-in signals show 0."}
trends={"venues":VEN,"labels":["","","",""],"weekno":["W22","W23","W24","W25"],
        "dateTY":["29 Jun–5 Jul","6–12 Jul","13–19 Jul","20–26 Jul"],
        "dateLY":["1–7 Jul","8–14 Jul","15–21 Jul","22–28 Jul"],
        "fyrange":"FY26 weeks 22–25","sym":"£","data":data,"narr":narr,"alert":alert,"sharednote":sharednote}
json.dump(trends,open(OUT+"_trends_payload.json","w"),indent=1,ensure_ascii=False)

# handoff
yoy_pct=round(yoyp,1)
handoff={"venues":[{"name":v,"weekly_bookings":actW25[v]} for v in VEN],
  "portfolio_bookings":tot_act,"portfolio_target":tot_tgt,"yoy_pct":yoy_pct,
  "deepdive_venues":DEEP,
  "ga4_meta":f"Portfolio {tot_act:,} · YoY {'▲' if yoyp>=0 else '▼'}{abs(yoyp):.1f}%",
  "ga4_yoy":f"{'▲' if yoyp>=0 else '▼'}{abs(yoyp):.1f}% YoY"}
json.dump(handoff,open(OUT+"_handoff.json","w"),indent=1,ensure_ascii=False)
print("VERIFY sum venue act =",tot_act,"; trend W25 GA4 sum =",sum(data[v][2][1][-1] for v in VEN))
print("trends W25 bookings per venue:",{v:data[v][2][1][-1] for v in VEN})
print("done")
