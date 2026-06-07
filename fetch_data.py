"""
MarketIQ - NSE Data Fetcher (Nifty 500 Edition)
Runs via GitHub Actions every 30 minutes
Automatically fetches all 500 stocks from NSE and runs VCP/Squeeze math
"""
import yfinance as yf
import json
import csv
import requests
from datetime import datetime, timezone, timedelta
import time
import sys

INDICES = [
    ("^NSEI",      "Nifty 50"),
    ("^NSEBANK",   "Nifty Bank"),
    ("^CNXIT",     "Nifty IT"),
    ("^CNXPHARMA", "Nifty Pharma"),
    ("^CNXAUTO",   "Nifty Auto"),
    ("^CNXFMCG",   "Nifty FMCG"),
    ("^CNXMETAL",  "Nifty Metal"),
    ("^CNXENERGY", "Nifty Energy"),
]

RRG_PROXIES = {
    "I.T":         "^CNXIT",
    "Financials":  "^NSEBANK",
    "Healthcare":  "^CNXPHARMA",
    "Auto":        "^CNXAUTO",
    "FMCG":        "^CNXFMCG",
    "Metals":      "^CNXMETAL",
    "Energy":      "^CNXENERGY",
    "Industrials": "LT.NS",
    "Chemicals":   "ASIANPAINT.NS",
    "Consumer":    "TITAN.NS",
    "Realty":      "DLF.NS",
    "Telecom":     "BHARTIARTL.NS",
}

def safe(v, d=0.0):
    try:
        f = float(v)
        return d if f != f else round(f, 2)
    except:
        return d

def candle(o, h, l, c):
    try:
        o,h,l,c = safe(o,c),safe(h,c),safe(l,c),safe(c,0)
        body=abs(c-o); r=(h-l) or 0.001; bp=body/r
        uw=h-max(o,c); lw=min(o,c)-l
        if bp>.8: return "Bullish Marubozu" if c>o else "Bearish Marubozu"
        if bp<.1:
            if uw>2*lw: return "Shooting Star"
            if lw>2*uw: return "Dragonfly Doji"
            return "Doji"
        if c>o:
            if lw>2*body and uw<body: return "Hammer"
            if uw>2*body and lw<body: return "Inverted Hammer"
            return "Bullish Candle"
        if uw>2*body: return "Hanging Man"
        return "Bearish Candle"
    except:
        return "Bullish Candle"

def fetch_stock(sym, name, sector, mcap):
    try:
        h = yf.Ticker(sym).history(period="1y", interval="1d", auto_adjust=True)
        if h is None or h.empty or len(h) < 10:
            return None
        cl = [safe(x) for x in h["Close"] if safe(x)>0]
        op = [safe(x) for x in h["Open"]]
        hi = [safe(x) for x in h["High"]]
        lo = [safe(x) for x in h["Low"]]
        vo = [int(x) for x in h["Volume"]]
        dt = [str(d.date()) for d in h.index]
        if len(cl)<20: return None
        
        price=cl[-1]; prev=cl[-2]
        chg=round(price-prev,2)
        pct=round((chg/prev*100) if prev else 0,2)
        n=len(cl)
        
        ma20=round(sum(cl[-20:])/min(20,n),2)
        ma50=round(sum(cl[-50:])/min(50,n),2)
        ma150=round(sum(cl[-150:])/min(150,n),2) if n>=150 else ma50
        ma200=round(sum(cl[-200:])/min(200,n),2) if n>=200 else ma50
        
        hi52=round(max(hi[-250:]) if n>=250 else max(hi), 2)
        lo52=round(min(lo[-250:]) if n>=250 else min(lo), 2)
        
        trend=0
        for j in range(n-1,0,-1):
            if cl[j]>cl[j-1]: trend+=1
            else: break
            
        dl=[cl[i]-cl[i-1] for i in range(1,n)]
        gains=[d if d>0 else 0 for d in dl[-14:]]
        losses=[-d if d<0 else 0 for d in dl[-14:]]
        ag=sum(gains)/14 if gains else 0
        al=sum(losses)/14 if losses else 0.001
        rsi=round(100-100/(1+ag/al),1)
        trs=[hi[i]-lo[i] for i in range(max(0,n-14),n)]
        atr=round(sum(trs)/len(trs),2) if trs else 0
        
        r5=round((cl[-1]/cl[-5]-1)*100,2) if n>=5 else 0
        r20=round((cl[-1]/cl[-20]-1)*100,2) if n>=20 else 0
        r60=round((cl[-1]/cl[-60]-1)*100,2) if n>=60 else 0
        mom=round(r5*0.5+r20*0.3+r60*0.2,2)
        
        w=min(5,n); m=min(22,n); q=min(66,n)
        dc=candle(op[-1],hi[-1],lo[-1],cl[-1])
        wc=candle(op[-w],max(hi[-w:]),min(lo[-w:]),cl[-1])
        mc=candle(op[-m],max(hi[-m:]),min(lo[-m:]),cl[-1])
        qc=candle(op[-q],max(hi[-q:]),min(lo[-q:]),cl[-1])
        
        sw=0
        if "bullish" in dc.lower(): sw+=25
        if price>ma20: sw+=20
        if price>ma50: sw+=15
        if 50<=rsi<=70: sw+=20
        if trend>=2: sw+=20
        
        # ──────────────────────────────────────────────
        # ADVANCED VCP & VOLUME SQUEEZE RADAR MATH
        # ──────────────────────────────────────────────
        # Stage 2 Uptrend verification (Minervini Template)
        stage2 = price > ma50 and price > ma150 and price > ma200 and ma150 > ma200
        near_highs = price >= hi52 * 0.78 and price >= lo52 * 1.25
        
        # Squeeze Contraction: Volatility and Volume Drying Up
        recent_trs = [hi[i]-lo[i] for i in range(max(0, n-5), n)]
        atr5 = sum(recent_trs)/5 if recent_trs else 1
        recent_vols = vo[-5:]
        vol5 = sum(recent_vols)/5 if recent_vols else 1
        
        old_trs = [hi[i]-lo[i] for i in range(max(0, n-25), max(0, n-5))]
        atr20 = sum(old_trs)/20 if old_trs else 1
        old_vols = vo[-25:-5]
        vol20 = sum(old_vols)/20 if old_vols else 1
        
        vcp_squeeze = stage2 and near_highs and (atr5 < atr20 * 0.88) and (vol5 < vol20 * 0.75)

        return {
            "sym":sym.replace(".NS",""),"name":name,"sector":sector,"mcap":mcap,
            "price":price,"chg":chg,"chgPct":pct,
            "open":op[-1],"high":hi[-1],"low":lo[-1],"vol":vo[-1] if vo else 0,
            "dCandle":dc,"wCandle":wc,"mCandle":mc,"qCandle":qc,
            "trend":trend,"near52w":price>=hi52*0.95,"hi52":hi52,
            "rsi":rsi,"atr":atr,"ma20":ma20,"ma50":ma50,
            "ret5d":r5,"ret20d":r20,"ret60d":r60,"momScore":mom,
            "swingScore":sw,"aboveMA20":price>ma20,"aboveMA50":price>ma50,
            "isVCP": bool(vcp_squeeze),
            "dt":dt[-1] if dt else "—"
        }
    except:
        return None

def fetch_index(sym, name):
    try:
        h = yf.Ticker(sym).history(period="5d", interval="1d", auto_adjust=True)
        if h is None or h.empty or len(h)<2: return None
        cl=[safe(x) for x in h["Close"] if safe(x)>0]
        if len(cl)<2: return None
        price=cl[-1]; prev=cl[-2]
        chg=round(price-prev,2)
        pct=round((chg/prev*100) if prev else 0,2)
        return {"sym":sym,"name":name,"price":price,"chg":chg,"chgPct":pct,"dt":str(h.index[-1].date())}
    except: return None

def fetch_rrg_daily(proxy, bench_cl, bench_dt):
    try:
        h = yf.Ticker(proxy).history(period="3mo", interval="1d", auto_adjust=True)
        if h is None or h.empty or len(h)<10: return []
        sc=[safe(x) for x in h["Close"]]
        sd=[str(d.date()) for d in h.index]
        pts=[]; base=None
        for i,(d,c) in enumerate(zip(sd,sc)):
            if c<=0: continue
            bc=None
            for bd,bv in zip(bench_dt,bench_cl):
                if d == bd:
                    bc=bv; break
            if not bc or bc<=0: continue
            rs=c/bc
            if base is None: base=rs
            if not base: continue
            rn=(rs/base)*100
            rp=(sc[max(0,i-5)]/bc)/base*100 if i haste else rn
            pts.append({"date":d,"x":round(rn,3),"y":round(100+(rn-rp)*3.0,3)})
        return pts[-40:]
    except: return []

# ── MAIN ENGINE ENGINE ───────────────────────────
print("="*60)
print("MarketIQ Live Nifty 500 Automated Data Downloader")
print("="*60)

# Fetching the official Nifty 500 file directly from NSE
print("Downloading live Nifty 500 matrix list from NSE servers...")
STOCKS_LIST = []
try:
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    r = requests.get(url, headers=headers, timeout=15)
    lines = r.text.splitlines()
    reader = csv.reader(lines)
    header = next(reader) # skip headers
    
    count = 0
    for row in reader:
        if len(row) >= 3:
            sym = row[2].strip()
            name = row[0].strip()
            industry = row[1].strip()
            # Dynamic Cap Stratification by SEBI sizing rules
            if count <= 100: cap = "Largecap"
            elif count <= 250: cap = "Midcap"
            else: cap = "Smallcap"
            
            STOCKS_LIST.append((sym + ".NS", name, industry, cap))
            count += 1
except Exception as e:
    print(f"NSE Live Link failed ({e}). Running default fallbacks.")
    STOCKS_LIST = [((s[0] if s[0].endswith(".NS") else s[0]+".NS"), s[1], s[2], s[3]) for s in STOCKS]

if not STOCKS_LIST:
    print("Execution failure: No target symbols parsed."); sys.exit(1)

print(f"Targeting {len(STOCKS_LIST)} stocks across all caps.")

stocks=[]
for i, (sym,name,sec,mc) in enumerate(STOCKS_LIST):
    print(f"[{i+1}/{len(STOCKS_LIST)}] Processing {sym}...", end="", flush=True)
    r=fetch_stock(sym,name,sec,mc)
    if r:
        stocks.append(r)
        print(f" OK ({r['chgPct']:+.2f}%)")
    else:
        print(" SKIPPED")
    time.sleep(0.1) # Accelerated performance pipeline

stocks.sort(key=lambda x:x["chgPct"],reverse=True)

indices=[]
for sym,name in INDICES:
    r=fetch_index(sym,name)
    if r: indices.append(r)

print("\nProcessing Dynamic Daily Sector Rotation RRG Data...")
rrg={}
try:
    bh=yf.Ticker("^NSEI").history(period="3mo",interval="1d",auto_adjust=True)
    if bh is not None and not bh.empty:
        bc=[safe(x) for x in bh["Close"]]
        bd=[str(d.date()) for d in bh.index]
        for sec,proxy in RRG_PROXIES.items():
            pts=fetch_rrg_daily(proxy,bc,bd)
            rrg[sec]=pts
except Exception as e:
    print(f"RRG Pipeline Error: {e}")

sm={}
for s in stocks:
    k=s["sector"]
    if k not in sm: sm[k]={"name":k,"count":0,"pctSum":0,"momSum":0}
    sm[k]["count"]+=1; sm[k]["pctSum"]+=s["chgPct"]; sm[k]["momSum"]+=s["momScore"]
sectors=[{**v,"avgPct":round(v["pctSum"]/v["count"],2),"avgMom":round(v["momSum"]/v["count"],2)} for v in sm.values()]
sectors.sort(key=lambda x:x["avgPct"],reverse=True)

now=datetime.now(timezone.utc)
ist=now+timedelta(hours=5,minutes=30)

out={
    "fetchedAt": ist.strftime("%d/%m/%Y, %I:%M:%S %p")+" IST",
    "fetchedAtISO": now.isoformat(),
    "marketStatus": "Open" if 3<=now.hour<10 and now.weekday()<5 else "Closed",
    "totalStocks": len(stocks),
    "stocks": stocks,
    "indices": indices,
    "sectors": sectors,
    "rrgData": rrg,
    "swingPicks": sorted([s for s in stocks if s["swingScore"]>=60],key=lambda x:x["swingScore"],reverse=True)[:15],
    "topGainers": sorted(stocks,key=lambda x:x["chgPct"],reverse=True)[:10],
    "topLosers":  sorted(stocks,key=lambda x:x["chgPct"])[:10],
    "near52w":    [s for s in stocks if s["near52w"]][:20],
    "trendStocks":sorted([s for s in stocks if s["trend"]>=2],key=lambda x:x["trend"],reverse=True)[:20],
}

with open("data.json","w") as f:
    json.dump(out,f,indent=2)
print("✅ data.json successfully updated via automated Nifty 500 Engine.")
