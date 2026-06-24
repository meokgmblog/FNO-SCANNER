import pandas as pd
import requests
import time
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
import streamlit as st
import plotly.graph_objects as go

# ============================================================
# CONFIGURATION & CONFIG SETTINGS
# ============================================================
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiI2M0FZSEUiLCJqdGkiOiI2YTMwY2UxNTY4ODI0Zjc3ZDc1NmU3NjgiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6ZmFsc2UsImlzRXh0ZW5kZWQiOnRydWUsImlhdCI6MTc4MTU4MzM4MSwiaXNzIjoidWR... [TRUNCATED FOR LENGTH - USE YOUR FULL ACCESS TOKEN HERE]"

st.set_page_config(page_title="Live Sector Scope Tracker", layout="wide")

# Use local files uploaded to your GitHub repository folder
EXCEL_FILE = "FNO all list.xlsx"
INSTRUMENT_FILE = "instruments.csv"

headers = {
    "Accept": "application/json",
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

INDEX_KEY_MAP = {
    "NIFTY50": "NSE_INDEX|Nifty 50",
    "SENSEX": "BSE_INDEX|SENSEX",
    "IT": "NSE_INDEX|Nifty IT",
    "FMCG": "NSE_INDEX|Nifty FMCG",
    "PHARMA": "NSE_INDEX|Nifty Pharma",
    "PVT BANK": "NSE_INDEX|Nifty Private Bank",
    "NIFTY MID SELECT": "NSE_INDEX|Nifty Midcap Select",
    "AUTO": "NSE_INDEX|Nifty Auto",
    "FIN SERVICE": "NSE_INDEX|Nifty Financial Services",
    "BANK": "NSE_INDEX|Nifty Bank",
    "CEMENT": "NSE_INDEX|Nifty Commodities",
    "ENERGY": "NSE_INDEX|Nifty Energy",
    "METAL": "NSE_INDEX|Nifty Metal",
    "PSU BANK": "NSE_INDEX|Nifty PSU Bank",
    "REALTY": "NSE_INDEX|Nifty Realty"
}

# Time Gatekeeper
def is_market_hours():
    ist_zone = ZoneInfo("Asia/Kolkata")
    now_ist = datetime.now(ist_zone)
    if now_ist.weekday() >= 5:
        return False
    return dt_time(9, 10) <= now_ist.time() <= dt_time(15, 31)

# ============================================================
# LOAD STRUCTURAL MAPS
# ============================================================
@st.cache_data(ttl=28800)
def load_data_structures():
    df = pd.read_excel(EXCEL_FILE)[["SYMBOL", "SECTOR"]].dropna(subset=["SECTOR"])
    df["SECTOR"] = df["SECTOR"].astype(str).str.strip().str.upper()
    df["SYMBOL"] = df["SYMBOL"].astype(str).str.strip()
    
    inst_df = pd.read_csv(INSTRUMENT_FILE)
    instrument_map = {}
    for _, row in inst_df.iterrows():
        seg = str(row["segment"]).strip()
        if seg in ["NSE_EQ", "NSE_INDEX", "BSE_INDEX"]:
            instrument_map[str(row["trading_symbol"]).strip()] = str(row["instrument_key"]).strip()
            
    sector_map = {}
    all_keys = []
    for _, row in df.iterrows():
        sym = row["SYMBOL"]
        sec = row["SECTOR"]
        if sym in instrument_map:
            # Clean matching definitions to match dashboard names
            if sec == "BANKS": sec = "BANK"
            if sec == "PVT BANKS": sec = "PVT BANK"
            if sec == "REALITY": sec = "REALTY"
            
            sector_map.setdefault(sec, []).append(sym)
            key = instrument_map[sym]
            if key not in all_keys:
                all_keys.append(key)
                
    return sector_map, instrument_map, all_keys

sector_map, instrument_map, all_keys_to_fetch = load_data_structures()

# ============================================================
# API DATA PROCESSING ENGINES
# ============================================================
def fetch_intraday_performance(instrument_key):
    url = f"https://api.upstox.com/v2/historical-candle/intraday/{instrument_key}/1minute"
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            candles = res.json()["data"]["candles"]
            if candles:
                live_ltp = float(candles[0][4])
                open_price = float(candles[-1][1]) # Day open reference calculation
                change_pct = ((live_ltp - open_price) / open_price) * 100
                return instrument_key, change_pct, live_ltp
    except:
        pass
    return instrument_key, None, None

def fetch_all_parallel(keys_list):
    snapshot = {}
    prices = {}
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(fetch_intraday_performance, k): k for k in keys_list}
        for future in as_completed(futures):
            key = futures[future]
            try:
                k, change_pct, ltp = future.result()
                if change_pct is not None:
                    snapshot[k] = change_pct
                    prices[k] = ltp
            except:
                pass
    return snapshot, prices

# ============================================================
# STREAMLIT UI RENDER RUNTIME
# ============================================================
st.title("📊 LIVE SECTOR SCOPE TRACKER")

# Running Parallel Engines
all_index_keys = list(INDEX_KEY_MAP.values())
live_snapshot, live_prices = fetch_all_parallel(all_keys_to_fetch + all_index_keys)

# Compile Dashboard Calculations
dashboard_rows = []
for sector_name, index_key in INDEX_KEY_MAP.items():
    idx_change = live_snapshot.get(index_key, 0.0)
    
    # Track stocks in this specific bucket
    symbols_in_sector = sector_map.get(sector_name, [])
    bullish, bearish = 0, 0
    stock_details = []
    
    for sym in symbols_in_sector:
        k = instrument_map.get(sym)
        if k in live_snapshot:
            chg = live_snapshot[k]
            ltp = live_prices[k]
            sign = "⬆️" if chg >= 0 else "⬇️"
            if chg >= 0: bullish += 1
            else: bearish += 1
            stock_details.append({"Symbol": sym, "Price": ltp, "Change %": f"{chg:+.2f}%", "Signal": sign, "RawChg": chg})
            
    dashboard_rows.append({
        "Sector": sector_name,
        "Multiplier": idx_change,
        "Stocks": stock_details,
        "Bullish": bullish,
        "Bearish": bearish,
        "Total": len(symbols_in_sector)
    })

# Sort calculations from Highest to Lowest Performance (Matches your layout)
dashboard_rows.sort(key=lambda x: x["Multiplier"], reverse=True)

sectors_sorted = [r["Sector"] for r in dashboard_rows]
multipliers_sorted = [r["Multiplier"] for r in dashboard_rows]
colors = ['#2ca02c' if m >= 0 else '#d62728' for m in multipliers_sorted]

# 1. Main Interactive Bar Graph
fig = go.Figure(data=[go.Bar(x=sectors_sorted, y=multipliers_sorted, marker_color=colors)])
fig.update_layout(template="plotly_dark", height=400, margin=dict(l=20, r=20, t=20, b=20))
st.plotly_chart(fig, use_container_width=True)

# 2. Clicking Action Area (Dropdown Syncs to the Bar Chart Order)
st.subheader("🔍 Explore Sector Profiles")
selected_sector = st.selectbox("Select a sector group to view performance updates:", sectors_sorted)

# Find corresponding row details matching user select action
sector_info = next(item for item in dashboard_rows if item["Sector"] == selected_sector)

# 3. Dynamic Sector Stocks Grid
st.markdown(f"### Component stock status inside: **{selected_sector}**")
stocks_list = sector_info["Stocks"]

if stocks_list:
    df_all_stocks = pd.DataFrame(stocks_list)
    df_up = df_all_stocks[df_all_stocks["RawChg"] >= 0].drop(columns=["RawChg"])
    df_down = df_all_stocks[df_all_stocks["RawChg"] < 0].drop(columns=["RawChg"])
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"🟢 **{len(df_up)} Stocks Up**")
        st.dataframe(df_up, use_container_width=True, hide_index=True)
    with col2:
        st.markdown(f"🔴 **{len(df_down)} Stocks Down**")
        st.dataframe(df_down, use_container_width=True, hide_index=True)
else:
    st.info("No matching live stock symbol tickers available for this sector mapping index right now.")

# Live loop re-run configuration
if is_market_hours():
    time.sleep(60)
    st.rerun()
else:
    st.caption(f"Paused. Current IST time is outside live trading parameters.")
