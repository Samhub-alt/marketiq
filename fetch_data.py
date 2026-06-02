"""
MarketIQ - NSE Data Fetcher
Runs via GitHub Actions every 30 minutes
Saves data to data.json in same folder
"""
import yfinance as yf
import json
from datetime import datetime, timezone, timedelta
import time
import sys

STOCKS = [
    ("TCS.NS",        "TCS",             "I.T",        "Largecap"),
    ("INFY.NS",       "Infosys",          "I.T",        "Largecap"),
    ("WIPRO.NS",      "Wipro",            "I.T",        "Largecap"),
    ("HCLTECH.NS",    "HCL Technologies", "I.T",        "Largecap"),
    ("TECHM.NS",      "Tech Mahindra",    "I.T",        "Largecap"),
    ("HDFCBANK.NS",   "HDFC Bank",        "Financials", "Largecap"),
    ("ICICIBANK.NS",  "ICICI Bank",       "Financials", "Largecap"),
    ("SBIN.NS",       "SBI",              "Financials", "Largecap"),
    ("AXISBANK.NS",   "Axis Bank",        "Financials", "Largecap"),
    ("KOTAKBANK.NS",  "Kotak Bank",       "Financials", "Largecap"),
    ("BAJFINANCE.NS", "Bajaj Finance",    "Financials", "Largecap"),
    ("SUNPHARMA.NS",  "Sun Pharma",       "Healthcare", "Largecap"),
    ("DRREDDY.NS",    "Dr. Reddys",       "Healthcare", "Largecap"),
    ("CIPLA.NS",      "Cipla",            "Healthcare", "Largecap"),
    ("DIVISLAB.NS",   "Divis Labs",       "Healthcare", "Largecap"),
    ("APOLLOHOSP.NS", "Apollo Hospitals", "Healthcare", "Largecap"),
    ("MARUTI.NS",     "Maruti Suzuki",    "Auto",       "Largecap"),
    ("TATAMOTORS.NS", "Tata Motors",      "Auto",       "Largecap"),
    ("BAJAJ-AUTO.NS", "Bajaj Auto",       "Auto",       "Largecap"),
    ("HEROMOTOCO.NS", "Hero MotoCorp",    "Auto",       "Largecap"),
    ("RELIANCE.NS",   "Reliance Ind.",    "Energy",     "Largecap"),
    ("ONGC.NS",       "ONGC",            "Energy",     "Largecap"),
    ("NTPC.NS",       "NTPC",            "Energy",     "Largecap"),
    ("POWERGRID.NS",  "Power Grid",      "Energy",     "Largecap"),
    ("HINDUNILVR.NS", "HUL",             "FMCG",       "Largecap"),
    ("NESTLEIND.NS",  "Nestle India",    "FMCG",       "Largecap"),
    ("ITC.NS",        "ITC",             "FMCG",       "Largecap"),
    ("BRITANNIA.NS",  "Britannia",       "FMCG",       "Largecap"),
    ("TATASTEEL.NS",  "Tata Steel",      "Metals",     "Largecap"),
    ("HINDALCO.NS",   "Hindalco",        "Metals",     "Largecap"),
    ("JSWSTEEL.NS",   "JSW Steel",       "Metals",     "Largecap"),
    ("COALINDIA.NS",  "Coal India",      "Metals",     "Largecap"),
    ("ASIANPAINT.NS", "Asian Paints",    "Chemicals",  "Largecap"),
    ("PIDILITIND.NS", "Pidilite",        "Chemicals",  "Midcap"),
    ("LT.NS",         "Larsen & Toubro", "Industrials","Largecap"),
    ("SIEMENS.NS",    "Siemens",         "Industrials","Largecap"),
    ("TITAN.NS",      "Titan",           "Consumer",   "Largecap"),
    ("DLF.NS",        "DLF",             "Realty",     "Largecap"),
    ("BHARTIARTL.NS", "Airtel",          "Telecom",    "Largecap"),
]

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
    for attempt in range(3):
        try:
            h = yf.Ticker(sym).history(period="1y", interval="1d", auto_adjust=True)
            if h is None or h.empty or len(h) < 5:
                time.sleep(2); continue
            cl = [safe(x) for x in h["Close"] if safe(x)>0]
            op = [safe(x) for x in h["Open"]]
            hi = [safe(x) for x in h["High"]]
            lo = [safe(x) for x in h["Low"]]
            vo = [int(x) for x in h["Volume"]]
            dt = [str(d.date()) for d in h.index]
            if len(cl)<5: continue
            price=cl[-1]; prev=cl[-2]
            chg=round(price-prev,2)
            pct=round((chg/prev*100) if prev else 0,2)
            n=len(cl)
            ma20=round(sum(cl[-20:])/min(20,n),2)
            ma50=round(sum(cl[-50:])/min(50,n),2)
            hi52=round(max(hi),2)
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
            return {
                "sym":sym.replace(".NS",""),"name":name,"sector":sector,"mcap":mcap,
                "price":price,"chg":chg,"chgPct":pct,
                "open":op[-1],"high":hi[-1],"low":lo[-1],"vol":vo[-1] if vo else 0,
                "dCandle":dc,"wCandle":wc,"mCandle":mc,"qCandle":qc,
                "trend":trend,"near52w":price>=hi52*0.95,"hi52":hi52,
                "rsi":rsi,"atr":atr,"ma20":ma20,"ma50":ma50,
                "ret5d":r5,"ret20d":r20,"ret60d":r60,"momScore":mom,
                "swingScore":sw,"aboveMA20":price>ma20,"aboveMA50":price>ma50,
                "dt":dt[-1] if dt else "—"
            }
        except Exception as e:
            print(f"  attempt {attempt+1} error: {e}")
            time.sleep(3)
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
    except Exception as e:
        print(f"  index {sym} error: {e}"); return None

def fetch_rrg(proxy, bench_cl, bench_dt):
    try:
        h = yf.Ticker(proxy).history(period="2y", interval="1wk", auto_adjust=True)
        if h is None or h.empty or len(h)<10: return []
        sc=[safe(x) for x in h["Close"]]
        sd=[str(d.date()) for d in h.index]
        pts=[]; base=None
        for i,(d,c) in enumerate(zip(sd,sc)):
            if c<=0: continue
            bc=None
            for bd,bv in zip(bench_dt,bench_cl):
                try:
                    if abs((datetime.strptime(d,"%Y-%m-%d")-datetime.strptime(bd,"%Y-%m-%d")).days)<=5:
                        bc=bv; break
                except: pass
            if not bc or bc<=0: continue
            rs=c/bc
            if base is None: base=rs
            if not base: continue
            rn=(rs/base)*100
            rp=(sc[max(0,i-4)]/bc)/base*100 if i>=4 else rn
            pts.append({"date":d,"x":round(rn,3),"y":round(100+(rn-rp)*2.5,3)})
        return pts[-52:] if len(pts)>52 else pts
    except Exception as e:
        print(f"  rrg {proxy} error: {e}"); return []

# ── MAIN ─────────────────────────────────────────
print("="*50)
print("MarketIQ NSE Fetcher starting...")
print("="*50)

# Fetch stocks
print(f"\nFetching {len(STOCKS)} stocks...")
stocks=[]
for sym,name,sec,mc in STOCKS:
    print(f"  {sym}...",end="",flush=True)
    r=fetch_stock(sym,name,sec,mc)
    if r:
        stocks.append(r)
        print(f" OK ₹{r['price']} ({r['chgPct']:+.2f}%)")
    else:
        print(" FAILED")
    time.sleep(0.5)

if not stocks:
    print("ERROR: No stocks fetched!"); sys.exit(1)

stocks.sort(key=lambda x:x["chgPct"],reverse=True)
print(f"\n✅ {len(stocks)} stocks fetched")

# Fetch indices
print(f"\nFetching {len(INDICES)} indices...")
indices=[]
for sym,name in INDICES:
    r=fetch_index(sym,name)
    if r:
        indices.append(r)
        print(f"  {name}: ₹{r['price']} ({r['chgPct']:+.2f}%)")
    time.sleep(0.3)

# Fetch RRG
print("\nFetching RRG data...")
rrg={}
try:
    bh=yf.Ticker("^NSEI").history(period="2y",interval="1wk",auto_adjust=True)
    if bh is not None and not bh.empty:
        bc=[safe(x) for x in bh["Close"]]
        bd=[str(d.date()) for d in bh.index]
        for sec,proxy in RRG_PROXIES.items():
            print(f"  {sec}...",end="",flush=True)
            pts=fetch_rrg(proxy,bc,bd)
            rrg[sec]=pts
            print(f" {len(pts)} weeks")
            time.sleep(0.3)
except Exception as e:
    print(f"RRG error: {e}")

# Build sectors
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
    "swingPicks": sorted([s for s in stocks if s["swingScore"]>=60],key=lambda x:x["swingScore"],reverse=True),
    "topGainers": sorted(stocks,key=lambda x:x["chgPct"],reverse=True)[:5],
    "topLosers":  sorted(stocks,key=lambda x:x["chgPct"])[:5],
    "near52w":    [s for s in stocks if s["near52w"]],
    "trendStocks":sorted([s for s in stocks if s["trend"]>=2],key=lambda x:x["trend"],reverse=True),
}

with open("data.json","w") as f:
    json.dump(out,f,indent=2)

print(f"\n{'='*50}")
print(f"✅ data.json saved!")
print(f"   Stocks: {len(stocks)}, Indices: {len(indices)}, RRG sectors: {len(rrg)}")
print(f"   Fetched at: {out['fetchedAt']}")
print(f"{'='*50}")
