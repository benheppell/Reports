# LY Google weekly buckets LW22(1-7),LW23(8-14),LW24(15-21),LW25(22-28): booking, signals, spend
ly={
"Aqua Shard":{"book":[912.16,953.41,1054.05,1047.12],"sig":[606.93,821.82,883.58,947.42],"spend":[1305.78,1422.30,1647.68,2192.62]},
"Hutong":{"book":[414.59,530.33,537.62,589.50],"sig":[595.67,539.00,567.50,623.50],"spend":[1289.76,1442.86,1365.83,1321.88]},
"Regent St":{"book":[81.5,67.5,103.0,79.5],"sig":[359,407,280,289],"spend":[1196.98,1134.86,1024.80,1040.78]},
"Azzurra":{"book":[27,39.06,28,26],"sig":[0,0,0,0],"spend":[654.68,666.38,662.14,676.10]},
"Shiro Sushi":{"book":[71.52,96.50,60.47,85.40],"sig":[373,511,471,540],"spend":[690.33,636.94,637.97,688.59]},
"DSL":{"book":[0,0,0,0],"sig":[0,0,0,0],"spend":[0,0,0,0]},
}
if __name__=="__main__":
    import json
    json.dump(ly,open("/sessions/vibrant-nice-lamport/mnt/Hong Kong/site/london/w2026-07-20/_raw/google_ly.json","w"))
    print("LY google recorded")
