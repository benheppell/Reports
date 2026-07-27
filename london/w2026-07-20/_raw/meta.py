# weeks order W22,W23,W24,W25 (TY) ; spend & schedules(offsite_conversion.fb_pixel_custom)
ty={
"Aqua Shard":{"spend":[1673.14,1942.08,2538.88,2841.49],"sch":[142,142,159,182]},
"Hutong":{"spend":[1711.26,1695.08,2074.68,2181.69],"sch":[122,137,150,231]},
"Kyoto":{"spend":[511.94,647.04,442.59,465.54],"sch":[30,38,28,33]},
"Nueva":{"spend":[540.64,576.42,569.80,578.23],"sch":[41,33,31,44]},
"Azzurra":{"spend":[1022.34,1139.34,1074.95,1150.79],"sch":[59,60,64,54]},
"Shiro Sushi":{"spend":[381.52,324.49,310.17,326.50],"sch":[30,29,30,40]},
"DSL":{"spend":[1600.18,1855.13,1791.07,1847.62],"sch":[76,97,93,148]},
}
# Regent St = Kyoto+Nueva
ty["Regent St"]={"spend":[round(ty["Kyoto"]["spend"][i]+ty["Nueva"]["spend"][i],2) for i in range(4)],
                 "sch":[ty["Kyoto"]["sch"][i]+ty["Nueva"]["sch"][i] for i in range(4)]}

ly={
"Aqua Shard":{"spend":[1107,1095.41,1087.63,1105.67],"sch":[136,133,118,166]},
"Hutong":{"spend":[569.07,553.29,557.41,611.71],"sch":[83,64,76,66]},
"Kyoto":{"spend":[265.27,267.14,262.84,240.24],"sch":[21,16,16,19]},
"Nueva":{"spend":[386.30,382.47,380.13,383.70],"sch":[5,5,13,7]},
"Azzurra":{"spend":[282.27,278.82,295.74,277.76],"sch":[2,3,13,14]},
"Shiro Sushi":{"spend":[339.14,357.62,345.88,317.89],"sch":[11,16,15,25]},
"DSL":{"spend":[590.96,576.61,577.45,584.94],"sch":[37,35,37,43]},
}
ly["Regent St"]={"spend":[round(ly["Kyoto"]["spend"][i]+ly["Nueva"]["spend"][i],2) for i in range(4)],
                 "sch":[ly["Kyoto"]["sch"][i]+ly["Nueva"]["sch"][i] for i in range(4)]}
if __name__=="__main__":
    import json
    json.dump({"ty":ty,"ly":ly},open("/sessions/vibrant-nice-lamport/mnt/Hong Kong/site/london/w2026-07-20/_raw/meta.json","w"))
    print("W25 meta:", {v:(ty[v]["spend"][-1],ty[v]["sch"][-1]) for v in ["Aqua Shard","Hutong","Regent St","Azzurra","Shiro Sushi","DSL"]})
